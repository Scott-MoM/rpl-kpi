from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import quote
import uuid

from fastapi import HTTPException, status
import requests

from ..db.supabase import get_supabase_server_client
from ..schemas.reports import (
    ReportAggregateRow,
    ReportResponse,
    ReportRow,
    ReportSummary,
    SaveReportRequest,
    SavedReport,
    UpdateReportSharingRequest,
)


class ReportsService:
    _fetch_batch_size = 250
    _fetch_row_limit = 5000
    _postcode_lookup_timeout = 6
    _routing_timeout = 8

    _dataset_config = {
        "People": {"table": "beacon_people", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Organisations": {"table": "beacon_organisations", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Events": {"table": "beacon_events", "date_col": "start_date", "select_cols": "payload, start_date, region"},
        "Payments": {"table": "beacon_payments", "date_col": "payment_date", "select_cols": "payload, payment_date"},
        "Grants": {"table": "beacon_grants", "date_col": "close_date", "select_cols": "payload, close_date"},
    }

    def __init__(self) -> None:
        self._postcode_cache: dict[str, tuple[float, float] | None] = {}
        self._road_distance_cache: dict[tuple[str, str], float | None] = {}

    def get_custom_report(
        self,
        dataset: list[str],
        region: str,
        timeframe: str,
        start_date: str | None = None,
        end_date: str | None = None,
        category_filter: list[str] | None = None,
        status_filter: list[str] | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        require_date: bool = False,
        group_by: str = "region",
        metric: str = "metric_value",
        aggregation: str = "sum",
    ) -> ReportResponse:
        client = get_supabase_server_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        datasets = dataset or ["Events", "Payments"]
        rows: list[dict[str, Any]] = []
        for dataset_key in datasets:
            if dataset_key == "Travel Distance":
                rows.extend(self._fetch_travel_distance_rows(client, start_date, end_date))
            else:
                rows.extend(self._fetch_dataset_rows(client, dataset_key, start_date, end_date))

        if region != "Global":
            rows = [row for row in rows if region.lower() in row["region"].lower()]
        if category_filter:
            rows = [row for row in rows if row["category"] in category_filter]
        if status_filter:
            rows = [row for row in rows if row["status"] in status_filter]
        if min_value is not None:
            rows = [row for row in rows if row["metric_value"] >= min_value]
        if max_value is not None:
            rows = [row for row in rows if row["metric_value"] <= max_value]
        if require_date:
            rows = [row for row in rows if row["date"]]

        available_group_by = [
            "dataset",
            "region",
            "category",
            "status",
            "month",
            "label",
            "attendee_postcode",
            "event_postcode",
            "attendee_label",
            "event_label",
        ]
        normalized_group_by = group_by if group_by in available_group_by else "region"
        normalized_metric = metric if metric in ("metric_value", "record_count", "distance_miles", "distance_km") else "metric_value"
        normalized_aggregation = aggregation if aggregation in ("sum", "count", "mean") else "sum"

        grouped_rows = self._aggregate_rows(rows, normalized_group_by, normalized_metric, normalized_aggregation)

        report_rows = [ReportRow(**row) for row in rows]
        summary = ReportSummary(
            row_count=len(rows),
            dataset_count=len(set(row["dataset"] for row in rows)) if rows else 0,
            total_metric_value=float(sum(row["metric_value"] for row in rows)),
        )
        return ReportResponse(
            report_type="custom",
            region=region,
            timeframe=timeframe,
            dataset=datasets,
            rows=report_rows,
            grouped_rows=grouped_rows,
            group_by=normalized_group_by,
            metric=normalized_metric,
            aggregation=normalized_aggregation,
            summary=summary,
            available_group_by=available_group_by,
        )

    def save_report(self, payload: SaveReportRequest) -> SavedReport:
        client = self._client()
        report_id = uuid.uuid4().hex[:12]
        details = {
            "source": "custom_reports",
            "report_id": report_id,
            "report_name": (payload.report_name or "").strip() or "Untitled Report",
            "owner_email": payload.owner_email.strip().lower(),
            "shared_with": self._normalize_email_list(payload.shared_with),
            "config": payload.config or {},
        }
        client.table("audit_logs").insert(
            {
                "user_email": details["owner_email"],
                "action": "Custom Report Saved",
                "details": details,
                "region": "Global",
            }
        ).execute()
        return SavedReport(
            report_id=report_id,
            name=details["report_name"],
            owner_email=details["owner_email"],
            shared_with=details["shared_with"],
            config=details["config"],
        )

    def update_report_sharing(self, payload: UpdateReportSharingRequest) -> SavedReport:
        client = self._client()
        details = {
            "source": "custom_reports",
            "report_id": payload.report_id,
            "report_name": payload.report_name,
            "owner_email": payload.owner_email.strip().lower(),
            "shared_with": self._normalize_email_list(payload.shared_with),
        }
        client.table("audit_logs").insert(
            {
                "user_email": details["owner_email"],
                "action": "Custom Report Share Updated",
                "details": details,
                "region": "Global",
            }
        ).execute()
        accessible = self.list_saved_reports(details["owner_email"])
        match = next((report for report in accessible if report.report_id == payload.report_id), None)
        return match or SavedReport(
            report_id=payload.report_id,
            name=payload.report_name,
            owner_email=details["owner_email"],
            shared_with=details["shared_with"],
            config={},
        )

    def list_saved_reports(self, user_email: str) -> list[SavedReport]:
        client = self._client()
        email = (user_email or "").strip().lower()
        if not email:
            return []
        try:
            rows = (
                client.table("audit_logs")
                .select("created_at, action, details")
                .in_("action", ["Custom Report Saved", "Custom Report Share Updated"])
                .order("created_at", desc=False)
                .limit(1000)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        reports: dict[str, dict[str, Any]] = {}
        for row in rows:
            details = row.get("details") or {}
            if details.get("source") != "custom_reports":
                continue
            report_id = details.get("report_id")
            if not report_id:
                continue
            report = reports.get(report_id, {})
            report["report_id"] = report_id
            report["name"] = details.get("report_name") or report.get("name") or "Untitled Report"
            report["owner_email"] = str(details.get("owner_email") or report.get("owner_email") or "").strip().lower()
            report["shared_with"] = self._normalize_email_list(details.get("shared_with") or report.get("shared_with") or [])
            if row.get("action") == "Custom Report Saved":
                report["config"] = details.get("config") or report.get("config") or {}
                if not report.get("created_at"):
                    report["created_at"] = row.get("created_at")
            report["updated_at"] = row.get("created_at")
            reports[report_id] = report

        accessible = []
        for report in reports.values():
            if report.get("owner_email") == email or email in report.get("shared_with", []):
                accessible.append(SavedReport(**report))
        accessible.sort(key=lambda item: str(item.updated_at or ""), reverse=True)
        return accessible

    def _fetch_dataset_rows(
        self,
        client,
        dataset_key: str,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        cfg = self._dataset_config.get(dataset_key)
        if not cfg:
            return []

        rows = []
        offset = 0
        batch_size = self._fetch_batch_size
        max_rows = self._fetch_row_limit
        while offset < max_rows:
            end_offset = min(offset + batch_size - 1, max_rows - 1)
            query = client.table(cfg["table"]).select(cfg["select_cols"]).range(offset, end_offset)
            if start_date:
                query = query.gte(cfg["date_col"], f"{start_date}T00:00:00")
            if end_date:
                query = query.lte(cfg["date_col"], f"{end_date}T23:59:59")
            query = query.order(cfg["date_col"], desc=True)
            chunk = query.execute().data or []
            rows.extend(chunk)
            if len(chunk) < batch_size:
                break
            offset += batch_size

        flattened = []
        for row in rows:
            payload = row.get("payload") or {}
            date_val = row.get(cfg["date_col"]) or payload.get(cfg["date_col"]) or payload.get("created_at") or payload.get("date")
            region_tags = self._to_list(payload.get("c_region"))
            region_name = (region_tags[0] if region_tags else None) or row.get("region") or payload.get("region") or "Other"
            item = {
                "dataset": dataset_key,
                "record_id": str(payload.get("id") or row.get("id") or ""),
                "date": self._normalize_date(date_val),
                "region": str(region_name).strip() if region_name else "Other",
                "category": "",
                "label": "",
                "status": "",
                "metric_value": 0.0,
                "record_count": 1,
                "month": self._month_bucket(date_val),
            }

            if dataset_key == "People":
                types = self._to_list(payload.get("type"))
                item["category"] = ", ".join(str(value) for value in types) if types else "Unknown"
                item["label"] = str(self._first_value(payload, "name", "full_name", "Name", "Display Name", "email") or payload.get("id") or "Person")
                item["metric_value"] = 1.0
            elif dataset_key == "Organisations":
                item["category"] = str(self._first_value(payload, "type", "Organisation type", "Organization type", "Category") or "Unknown")
                item["label"] = str(self._first_value(payload, "name", "Organisation", "Organization", "Display Name") or payload.get("id") or "Organisation")
                item["metric_value"] = 1.0
            elif dataset_key == "Events":
                item["category"] = str(self._first_value(payload, "type", "Event type", "Activity type", "Category") or "Event")
                item["label"] = str(self._first_value(payload, "name", "title", "Event name", "Description") or payload.get("id") or "Event")
                item["metric_value"] = self._coerce_float(
                    self._first_value(payload, "number_of_attendees", "Number of attendees", "Attendees", "Participants", "Participant count")
                )
            elif dataset_key == "Payments":
                item["category"] = str(self._first_value(payload, "type", "Payment type", "Category") or "Payment")
                item["label"] = str(self._first_value(payload, "description", "Name", "Payment", "Reference") or payload.get("id") or "Payment")
                item["status"] = str(self._first_value(payload, "status", "payment_status", "Payment Status") or "")
                item["metric_value"] = self._coerce_float(self._first_value(payload, "amount", "value", "total", "Amount", "Value"))
            elif dataset_key == "Grants":
                item["category"] = str(self._first_value(payload, "type", "Category", "Grant type") or "Grant")
                item["label"] = str(self._first_value(payload, "name", "title", "Grant", "Description") or payload.get("id") or "Grant")
                item["status"] = str(self._first_value(payload, "stage", "status", "Stage", "Status") or "")
                item["metric_value"] = self._coerce_float(self._first_value(payload, "amount", "amount_granted", "value", "Amount", "Value"))

            flattened.append(item)
        return flattened

    def _fetch_travel_distance_rows(
        self,
        client,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        events = self._fetch_raw_rows(client, "beacon_events", "payload, start_date, region", "start_date", start_date, end_date)
        attendees = self._fetch_raw_rows(client, "beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at", None, None)
        people = self._fetch_raw_rows(client, "beacon_people", "payload, created_at", "created_at", None, None)

        people_by_id: dict[str, dict[str, Any]] = {}
        for row in people:
            payload = row.get("payload") or {}
            person_id = payload.get("id") or row.get("id")
            if person_id is not None:
                people_by_id[self._entity_ref_key(person_id)] = payload

        events_by_id: dict[str, dict[str, Any]] = {}
        for row in events:
            payload = row.get("payload") or {}
            event_id = payload.get("id") or row.get("id")
            if event_id is None:
                continue
            enriched = dict(payload)
            enriched["_start_date"] = row.get("start_date") or payload.get("start_date")
            enriched["_region"] = row.get("region") or payload.get("region")
            events_by_id[str(event_id)] = enriched
            events_by_id[self._entity_ref_key(event_id)] = enriched

        flattened: list[dict[str, Any]] = []
        for row in attendees:
            payload = row.get("payload") or {}
            event_id = payload.get("event_id") or row.get("event_id")
            person_id = payload.get("person_id") or row.get("person_id")
            if not event_id:
                continue
            event = events_by_id.get(str(event_id)) or events_by_id.get(self._entity_ref_key(event_id))
            if not event:
                continue

            person = people_by_id.get(self._entity_ref_key(person_id)) if person_id else None
            attendee_postcode = self._normalize_postcode(
                self._first_value(
                    payload,
                    "postcode",
                    "postal_code",
                    "zip",
                    "home_postcode",
                    "address_postcode",
                )
                or self._first_value(
                    person or {},
                    "postcode",
                    "postal_code",
                    "zip",
                    "home_postcode",
                    "address_postcode",
                )
            )
            event_postcode = self._normalize_postcode(
                self._first_value(
                    event,
                    "postcode",
                    "postal_code",
                    "zip",
                    "event_postcode",
                    "venue_postcode",
                    "location_postcode",
                )
            )

            if not attendee_postcode or not event_postcode:
                continue

            distance_km = self._road_distance_km(attendee_postcode, event_postcode)
            if distance_km is None:
                continue

            attendee_label = str(
                self._first_value(
                    payload,
                    "name",
                    "full_name",
                    "participant_name",
                    "attendee_name",
                    "email",
                )
                or self._first_value(
                    person or {},
                    "name",
                    "full_name",
                    "Display Name",
                    "email",
                )
                or person_id
                or "Attendee"
            )
            event_label = str(
                self._first_value(
                    event,
                    "name",
                    "title",
                    "Event name",
                    "Description",
                )
                or event_id
                or "Event"
            )
            region_name = (
                self._first_value(event, "region")
                or event.get("_region")
                or (self._to_list(event.get("c_region"))[0] if self._to_list(event.get("c_region")) else None)
                or "Other"
            )
            date_val = event.get("_start_date") or event.get("start_date") or event.get("date")
            distance_miles = round(distance_km * 0.621371, 2)
            distance_km = round(distance_km, 2)
            flattened.append(
                {
                    "dataset": "Travel Distance",
                    "record_id": f"{event_id}:{person_id or attendee_label}",
                    "date": self._normalize_date(date_val),
                    "region": str(region_name).strip() if region_name else "Other",
                    "category": self._distance_band(distance_miles),
                    "label": f"{attendee_label} -> {event_label}",
                    "status": "Road route calculated",
                    "metric_value": distance_miles,
                    "record_count": 1,
                    "month": self._month_bucket(date_val),
                    "attendee_postcode": attendee_postcode,
                    "event_postcode": event_postcode,
                    "attendee_label": attendee_label,
                    "event_label": event_label,
                    "distance_miles": distance_miles,
                    "distance_km": distance_km,
                }
            )

        return flattened

    def _fetch_raw_rows(
        self,
        client,
        table: str,
        select_cols: str,
        date_col: str,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        batch_size = self._fetch_batch_size
        max_rows = self._fetch_row_limit
        while offset < max_rows:
            end_offset = min(offset + batch_size - 1, max_rows - 1)
            query = client.table(table).select(select_cols).range(offset, end_offset)
            if start_date:
                query = query.gte(date_col, f"{start_date}T00:00:00")
            if end_date:
                query = query.lte(date_col, f"{end_date}T23:59:59")
            query = query.order(date_col, desc=True)
            chunk = query.execute().data or []
            rows.extend(chunk)
            if len(chunk) < batch_size:
                break
            offset += batch_size
        return rows

    def _aggregate_rows(self, rows: list[dict[str, Any]], group_by: str, metric: str, aggregation: str) -> list[ReportAggregateRow]:
        buckets: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            key = str(row.get(group_by) or "Unknown")
            if aggregation == "count":
                buckets[key].append(1.0)
            else:
                buckets[key].append(float(row.get(metric) or 0))

        aggregated: list[ReportAggregateRow] = []
        for key, values in buckets.items():
            if aggregation == "mean":
                value = sum(values) / len(values) if values else 0.0
            else:
                value = sum(values)
            aggregated.append(ReportAggregateRow(key=key, value=float(value)))
        aggregated.sort(key=lambda item: item.value, reverse=True)
        return aggregated

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return value
        return None

    def _to_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _coerce_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(str(value).replace(",", "").replace("£", "").strip() or 0)
        except ValueError:
            return 0.0

    def _normalize_date(self, value: Any) -> str | None:
        if not value:
            return None
        return str(value)

    def _normalize_email_list(self, values: list[str] | None) -> list[str]:
        if not values:
            return []
        output: list[str] = []
        seen: set[str] = set()
        for value in values:
            email = str(value).strip().lower()
            if not email or email in seen:
                continue
            seen.add(email)
            output.append(email)
        return output

    def _client(self):
        client = get_supabase_server_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )
        return client

    def _month_bucket(self, value: Any) -> str | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text).strftime("%Y-%m")
        except ValueError:
            return None

    def _normalize_postcode(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip().upper().replace(" ", "")
        if len(text) < 5:
            return None
        return text

    def _postcode_coordinates(self, postcode: str) -> tuple[float, float] | None:
        normalized = self._normalize_postcode(postcode)
        if not normalized:
            return None
        if normalized in self._postcode_cache:
            return self._postcode_cache[normalized]
        try:
            response = requests.get(
                f"https://api.postcodes.io/postcodes/{quote(normalized)}",
                timeout=self._postcode_lookup_timeout,
            )
            response.raise_for_status()
            data = response.json().get("result") or {}
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            if latitude is None or longitude is None:
                coords = None
            else:
                coords = (float(latitude), float(longitude))
        except Exception:
            coords = None
        self._postcode_cache[normalized] = coords
        return coords

    def _road_distance_km(self, origin_postcode: str, destination_postcode: str) -> float | None:
        origin = self._normalize_postcode(origin_postcode)
        destination = self._normalize_postcode(destination_postcode)
        if not origin or not destination:
            return None
        cache_key = (origin, destination)
        if cache_key in self._road_distance_cache:
            return self._road_distance_cache[cache_key]

        origin_coords = self._postcode_coordinates(origin)
        destination_coords = self._postcode_coordinates(destination)
        if not origin_coords or not destination_coords:
            self._road_distance_cache[cache_key] = None
            return None

        origin_lat, origin_lon = origin_coords
        destination_lat, destination_lon = destination_coords
        try:
            response = requests.get(
                f"https://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}",
                params={"overview": "false"},
                timeout=self._routing_timeout,
            )
            response.raise_for_status()
            routes = response.json().get("routes") or []
            distance_meters = routes[0].get("distance") if routes else None
            distance_km = float(distance_meters) / 1000 if distance_meters is not None else None
        except Exception:
            distance_km = None

        self._road_distance_cache[cache_key] = distance_km
        return distance_km

    def _distance_band(self, distance_miles: float) -> str:
        lower = int(distance_miles // 10) * 10
        upper = lower + 9
        if lower == 0:
            return "0 to 9 miles"
        return f"{lower} to {upper} miles"

    def _entity_ref_key(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        return str(value).strip().lower()
