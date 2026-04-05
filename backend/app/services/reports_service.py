from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
import uuid

from fastapi import HTTPException, status

from app.db.supabase import get_supabase_client
from app.schemas.reports import (
    ReportAggregateRow,
    ReportResponse,
    ReportRow,
    ReportSummary,
    SaveReportRequest,
    SavedReport,
    UpdateReportSharingRequest,
)


class ReportsService:
    _dataset_config = {
        "People": {"table": "beacon_people", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Organisations": {"table": "beacon_organisations", "date_col": "created_at", "select_cols": "payload, created_at"},
        "Events": {"table": "beacon_events", "date_col": "start_date", "select_cols": "payload, start_date, region"},
        "Payments": {"table": "beacon_payments", "date_col": "payment_date", "select_cols": "payload, payment_date"},
        "Grants": {"table": "beacon_grants", "date_col": "close_date", "select_cols": "payload, close_date"},
    }

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
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        datasets = dataset or ["Events", "Payments"]
        rows: list[dict[str, Any]] = []
        for dataset_key in datasets:
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

        available_group_by = ["dataset", "region", "category", "status", "month", "label"]
        normalized_group_by = group_by if group_by in available_group_by else "region"
        normalized_metric = metric if metric in ("metric_value", "record_count") else "metric_value"
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
        batch_size = 1000
        while True:
            query = client.table(cfg["table"]).select(cfg["select_cols"]).range(offset, offset + batch_size - 1)
            if start_date:
                query = query.gte(cfg["date_col"], f"{start_date}T00:00:00")
            if end_date:
                query = query.lte(cfg["date_col"], f"{end_date}T23:59:59")
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
        client = get_supabase_client()
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
