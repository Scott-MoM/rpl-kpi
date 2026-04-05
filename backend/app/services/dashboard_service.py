from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from ..db.supabase import get_supabase_server_client
from ..schemas.dashboards import (
    DashboardDetailPayload,
    DashboardDetailRow,
    DashboardFilterOptions,
    DashboardSeriesPoint,
    FunderDetailPayload,
    DashboardMetric,
    MLEventDetailPayload,
    DashboardPayload,
    DashboardSection,
    DashboardSummary,
)


class DashboardService:
    _fetch_batch_size = 250
    _fetch_row_limit = 5000

    def list_dashboard_sections(self) -> list[DashboardSummary]:
        return [
            DashboardSummary(key="kpi", label="KPI Dashboard", description="Regional KPI overview and drill-downs."),
            DashboardSummary(key="funder", label="Funder Dashboard", description="Aggregated funder-safe metrics."),
            DashboardSummary(key="ml", label="ML Dashboard", description="Mountain leader event and attendee views."),
        ]

    def get_kpi_dashboard(self, region: str, start_date: str | None, end_date: str | None) -> DashboardPayload:
        result = self._load_dashboard_data("kpi", region, start_date, end_date)
        return self._build_payload("KPI Dashboard", region, start_date, end_date, result)

    def get_funder_dashboard(self, region: str, start_date: str | None, end_date: str | None) -> DashboardPayload:
        result = self._load_dashboard_data("funder", region, start_date, end_date)
        return self._build_payload("Funder Dashboard", region, start_date, end_date, result)

    def get_ml_dashboard(self, region: str, start_date: str | None, end_date: str | None) -> DashboardPayload:
        result = self._load_dashboard_data("ml", region, start_date, end_date)
        return self._build_payload("ML Dashboard", region, start_date, end_date, result)

    def get_filter_options(self) -> DashboardFilterOptions:
        client = get_supabase_server_client()
        if not client:
            return DashboardFilterOptions(regions=["Global"])

        try:
            rows = client.table("beacon_events").select("region").limit(5000).execute().data or []
        except Exception:
            rows = []

        regions = {"Global"}
        for row in rows:
            value = str(row.get("region") or "").strip()
            if value:
                regions.add(value)
        return DashboardFilterOptions(regions=sorted(regions))

    def get_kpi_section_detail(
        self,
        section: str,
        region: str,
        start_date: str | None,
        end_date: str | None,
    ) -> DashboardDetailPayload:
        result = self._load_dashboard_data("kpi", region, start_date, end_date)
        timeframe = f"{start_date or 'All time'} to {end_date or 'Now'}"
        rows = self._build_detail_rows(section, result)
        return DashboardDetailPayload(section=section, region=region, timeframe=timeframe, rows=rows)

    def get_ml_detail(
        self,
        region: str,
        start_date: str | None,
        end_date: str | None,
    ) -> DashboardDetailPayload:
        result = self._load_dashboard_data("ml", region, start_date, end_date)
        timeframe = f"{start_date or 'All time'} to {end_date or 'Now'}"
        rows = self._build_detail_rows("delivery", result)
        return DashboardDetailPayload(section="delivery", region=region, timeframe=timeframe, rows=rows)

    def get_ml_event_detail(
        self,
        event_id: str,
        region: str,
        start_date: str | None,
        end_date: str | None,
    ) -> MLEventDetailPayload:
        result = self._load_dashboard_data("ml", region, start_date, end_date)
        events = result.get("_raw_kpi", {}).get("delivery_events") or []
        selected = next((event for event in events if str(event.get("id")) == str(event_id)), None)
        if not selected:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

        raw_event = selected.get("raw_event") or {}
        sources = []
        attendee_records = selected.get("attendee_records") or []
        if attendee_records:
            sources.extend(attendee_records)

        return MLEventDetailPayload(
            event_id=str(selected.get("id") or event_id),
            label=str(selected.get("name") or raw_event.get("name") or event_id),
            date=selected.get("date"),
            region=str(selected.get("region") or ""),
            event_type=str(selected.get("type") or ""),
            participants=self._coerce_int(selected.get("participants")),
            metadata=self._rows_from_mapping(
                {
                    "Event ID": selected.get("id") or raw_event.get("id"),
                    "Event Name": selected.get("name") or raw_event.get("name"),
                    "Date": selected.get("date") or raw_event.get("start_date") or raw_event.get("date"),
                    "Region": selected.get("region") or ", ".join(str(value) for value in self._to_list(raw_event.get("c_region"))),
                    "Event Type": selected.get("type") or raw_event.get("type") or raw_event.get("category"),
                    "Participants": selected.get("participants"),
                    "Location": raw_event.get("location") or raw_event.get("venue"),
                    "Status": raw_event.get("status"),
                    "Description": raw_event.get("description"),
                },
                prefix="meta",
            ),
            personal_rows=self._collect_keyword_rows(sources, ("name", "full_name", "display_name", "email", "phone", "mobile", "dob", "address", "postcode", "gender")),
            medical_rows=self._collect_keyword_rows(sources, ("medical", "health", "medication", "condition", "allergy", "fitness", "dietary", "doctor")),
            emergency_rows=self._collect_keyword_rows(sources, ("emergency", "emergency_contact", "next_of_kin", "contact_person", "contact_name", "contact_phone")),
        )

    def get_funder_detail(
        self,
        funder: str,
        region: str,
        start_date: str | None,
        end_date: str | None,
    ) -> FunderDetailPayload:
        result = self._load_dashboard_data("funder", region, start_date, end_date)
        timeframe = f"{start_date or 'All time'} to {end_date or 'Now'}"
        raw_income = result.get("_raw_income", {}) or {}
        payments = raw_income.get("payments") or []
        grants = raw_income.get("grants") or []

        rows: list[DashboardDetailRow] = []
        income_buckets: dict[tuple[str, str], float] = {}
        selected_funder = funder.strip() or "All Funders"
        for payment in payments:
            matched_funder = self._extract_funder_name(payment)
            if selected_funder != "All Funders" and self._norm_key(matched_funder) != self._norm_key(selected_funder):
                continue
            amount = self._coerce_money(payment.get("amount"))
            date_value = payment.get("payment_date") or payment.get("date") or payment.get("created_at")
            rows.append(
                DashboardDetailRow(
                    id=f"payment-{payment.get('id') or len(rows)}",
                    label=str(self._get_row_value(payment, "description", "name", "reference") or payment.get("id") or "Payment"),
                    date=str(date_value or ""),
                    value=amount,
                    metadata={"source": "Payments", "funder": matched_funder},
                )
            )
            bucket = (self._month_bucket(date_value) or "Unknown", "Payments")
            income_buckets[bucket] = income_buckets.get(bucket, 0.0) + amount

        bids_submitted = 0
        total_funds = sum(row.value or 0 for row in rows)
        for grant in grants:
            matched_funder = self._extract_funder_name(grant)
            if selected_funder != "All Funders" and self._norm_key(matched_funder) != self._norm_key(selected_funder):
                continue
            amount = self._coerce_money(grant.get("amount"))
            stage = str(grant.get("stage") or "").lower()
            date_value = grant.get("close_date") or grant.get("award_date") or grant.get("created_at")
            rows.append(
                DashboardDetailRow(
                    id=f"grant-{grant.get('id') or len(rows)}",
                    label=str(self._get_row_value(grant, "name", "title", "description") or grant.get("id") or "Grant"),
                    date=str(date_value or ""),
                    value=amount,
                    metadata={"source": "Grants", "stage": stage or "", "funder": matched_funder},
                )
            )
            if any(token in stage for token in ["submitted", "review", "pending"]):
                bids_submitted += 1
            if stage == "won":
                total_funds += amount
            bucket = (self._month_bucket(date_value) or "Unknown", "Grants")
            income_buckets[bucket] = income_buckets.get(bucket, 0.0) + amount

        income_series = [
            DashboardSeriesPoint(label=label, series=series, value=value)
            for (label, series), value in sorted(income_buckets.items(), key=lambda item: item[0][0])
        ]
        metrics = [
            DashboardMetric(label="Bids Submitted", value=bids_submitted),
            DashboardMetric(label="Total Funds Raised", value=self._format_currency(total_funds)),
            DashboardMetric(label="Rows", value=len(rows)),
        ]
        return FunderDetailPayload(
            funder=selected_funder,
            region=region,
            timeframe=timeframe,
            metrics=metrics,
            income_series=income_series,
            rows=rows,
        )

    def _build_payload(
        self,
        title: str,
        region: str,
        start_date: str | None,
        end_date: str | None,
        result: dict[str, Any],
    ) -> DashboardPayload:
        timeframe = f"{start_date or 'All time'} to {end_date or 'Now'}"
        governance = result.get("governance", {})
        partnerships = result.get("partnerships", {})
        delivery = result.get("delivery", {})
        income = result.get("income", {})

        metrics = [
            DashboardMetric(label="Steering Members", value=governance.get("steering_members", 0)),
            DashboardMetric(label="Volunteers", value=governance.get("volunteers_new", 0)),
            DashboardMetric(label="Active Referrals", value=partnerships.get("active_referrals", 0)),
            DashboardMetric(label="Walks Delivered", value=delivery.get("walks_delivered", 0)),
            DashboardMetric(label="Participants", value=delivery.get("participants", 0)),
            DashboardMetric(label="Funds Raised", value=self._format_currency(income.get("total_funds_raised", 0))),
        ]

        sections = [
            DashboardSection(
                title="Governance",
                metrics=[
                    DashboardMetric(label="Steering Group Active", value="Yes" if governance.get("steering_group_active") else "No"),
                    DashboardMetric(label="Steering Members", value=governance.get("steering_members", 0)),
                    DashboardMetric(label="Volunteers", value=governance.get("volunteers_new", 0)),
                ],
            ),
            DashboardSection(
                title="Partnerships",
                metrics=[
                    DashboardMetric(label="Active Referrals", value=partnerships.get("active_referrals", 0)),
                    DashboardMetric(label="Networks Sat On", value=partnerships.get("networks_sat_on", 0)),
                    DashboardMetric(label="LSP Types", value=self._format_mapping(partnerships.get("LSP", {}))),
                    DashboardMetric(label="LDP Types", value=self._format_mapping(partnerships.get("LDP", {}))),
                ],
            ),
            DashboardSection(
                title="Delivery",
                metrics=[
                    DashboardMetric(label="Walks Delivered", value=delivery.get("walks_delivered", 0)),
                    DashboardMetric(label="Participants", value=delivery.get("participants", 0)),
                    DashboardMetric(label="Demographics", value=self._format_mapping(delivery.get("demographics", {}))),
                    DashboardMetric(
                        label="Demographic Source",
                        value=delivery.get("demographics_source", "unknown"),
                    ),
                ],
            ),
            DashboardSection(
                title="Income",
                metrics=[
                    DashboardMetric(label="Bids Submitted", value=income.get("bids_submitted", 0)),
                    DashboardMetric(label="Funds Raised", value=self._format_currency(income.get("total_funds_raised", 0))),
                    DashboardMetric(label="Corporate Partners", value=income.get("corporate_partners", 0)),
                    DashboardMetric(label="In-Kind Value", value=self._format_currency(income.get("in_kind_value", 0))),
                ],
            ),
        ]

        notes = [
            "This API response is generated from the existing Beacon/Supabase data model rather than Streamlit session state.",
            f"Data source: {result.get('_source', 'supabase')}.",
        ]

        return DashboardPayload(
            title=title,
            region=region,
            timeframe=timeframe,
            source=result.get("_source", "supabase"),
            last_updated=result.get("last_updated"),
            metrics=metrics,
            sections=sections,
            notes=notes,
        )

    def _build_detail_rows(self, section: str, result: dict[str, Any]) -> list[DashboardDetailRow]:
        section_key = section.strip().lower()
        raw = result.get("_raw_kpi", {})

        if section_key == "governance":
            rows = raw.get("region_people", [])
            return [
                DashboardDetailRow(
                    id=str(row.get("id") or index),
                    label=str(self._get_row_value(row, "name", "full_name", "Display Name", "email") or f"Person {index + 1}"),
                    date=row.get("created_at"),
                    region=", ".join(str(value) for value in self._to_list(row.get("c_region"))),
                    metadata={
                        "type": ", ".join(str(value) for value in self._to_list(row.get("type"))),
                    },
                )
                for index, row in enumerate(rows)
            ]

        if section_key == "partnerships":
            rows = raw.get("region_orgs", [])
            return [
                DashboardDetailRow(
                    id=str(row.get("id") or index),
                    label=str(self._get_row_value(row, "name", "title", "organisation_name") or f"Organisation {index + 1}"),
                    date=row.get("created_at"),
                    region=", ".join(str(value) for value in self._to_list(row.get("c_region"))),
                    metadata={
                        "type": str(row.get("type") or ""),
                    },
                )
                for index, row in enumerate(rows)
            ]

        if section_key == "delivery":
            rows = raw.get("delivery_events", [])
            return [
                DashboardDetailRow(
                    id=str(row.get("id") or index),
                    label=str(row.get("name") or f"Event {index + 1}"),
                    date=row.get("date"),
                    region=str(row.get("region") or ""),
                    value=row.get("participants"),
                    metadata={
                        "type": str(row.get("type") or ""),
                    },
                )
                for index, row in enumerate(rows)
            ]

        if section_key == "income":
            grants = raw.get("region_grants", [])
            payments = raw.get("region_payments", [])
            detail_rows: list[DashboardDetailRow] = []
            for index, row in enumerate(grants):
                detail_rows.append(
                    DashboardDetailRow(
                        id=f"grant-{row.get('id') or index}",
                        label=str(self._get_row_value(row, "name", "title", "stage") or f"Grant {index + 1}"),
                        date=row.get("close_date"),
                        value=self._coerce_money(row.get("amount")),
                        metadata={"kind": "Grant", "stage": str(row.get("stage") or "")},
                    )
                )
            for index, row in enumerate(payments):
                detail_rows.append(
                    DashboardDetailRow(
                        id=f"payment-{row.get('id') or index}",
                        label=str(self._get_row_value(row, "name", "title", "description") or f"Payment {index + 1}"),
                        date=row.get("payment_date"),
                        value=self._coerce_money(row.get("amount")),
                        metadata={"kind": "Payment"},
                    )
                )
            return detail_rows

        return []

    def _load_dashboard_data(
        self,
        dashboard_kind: str,
        region: str,
        start_date: str | None,
        end_date: str | None,
    ) -> dict[str, Any]:
        client = get_supabase_server_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        fetch_map = {
            "kpi": {
                "people": ("beacon_people", "payload, created_at", "created_at"),
                "organisations": ("beacon_organisations", "payload, created_at", "created_at"),
                "events": ("beacon_events", "payload, start_date, region", "start_date"),
                "attendees": ("beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at"),
                "payments": ("beacon_payments", "payload, payment_date", "payment_date"),
                "grants": ("beacon_grants", "payload, close_date", "close_date"),
            },
            "funder": {
                "people": ("beacon_people", "payload, created_at", "created_at"),
                "organisations": ("beacon_organisations", "payload, created_at", "created_at"),
                "events": ("beacon_events", "payload, start_date, region", "start_date"),
                "payments": ("beacon_payments", "payload, payment_date", "payment_date"),
                "grants": ("beacon_grants", "payload, close_date", "close_date"),
            },
            "ml": {
                "people": ("beacon_people", "payload, created_at", "created_at"),
                "events": ("beacon_events", "payload, start_date, region", "start_date"),
                "attendees": ("beacon_event_attendees", "payload, event_id, person_id, created_at", "created_at"),
            },
        }

        selections = fetch_map[dashboard_kind]
        start_iso = self._to_iso_boundary(start_date, is_end=False)
        end_iso = self._to_iso_boundary(end_date, is_end=True)

        rows: dict[str, list[dict[str, Any]]] = {}
        for key, (table, columns, date_field) in selections.items():
            rows[key] = self._fetch_supabase_rows(client, table, columns, date_field, start_iso, end_iso)

        people = self._rows_to_payloads(rows.get("people", []), date_field="created_at")
        organisations = self._rows_to_payloads(rows.get("organisations", []), date_field="created_at")
        events = self._rows_to_payloads(rows.get("events", []), date_field="start_date", region_field="region")
        payments = self._rows_to_payloads(rows.get("payments", []), date_field="payment_date")
        grants = self._rows_to_payloads(rows.get("grants", []), date_field="close_date")
        event_attendee_records = self._build_event_attendee_records(rows.get("attendees", []))

        result = self._compute_kpis(region, people, organisations, events, payments, grants, event_attendee_records)
        result["_source"] = f"supabase_{dashboard_kind}"
        return result

    def _fetch_supabase_rows(
        self,
        client,
        table: str,
        columns: str,
        date_field: str | None = None,
        start_iso: str | None = None,
        end_iso: str | None = None,
        batch_size: int | None = None,
        max_rows: int | None = None,
    ) -> list[dict[str, Any]]:
        resolved_batch_size = batch_size or self._fetch_batch_size
        resolved_max_rows = max_rows or self._fetch_row_limit
        rows: list[dict[str, Any]] = []
        offset = 0
        while offset < resolved_max_rows:
            query = client.table(table).select(columns)
            if date_field and start_iso:
                query = query.gte(date_field, start_iso)
            if date_field and end_iso:
                query = query.lte(date_field, end_iso)
            if date_field:
                query = query.order(date_field, desc=True)
            end_offset = min(offset + resolved_batch_size - 1, resolved_max_rows - 1)
            chunk = query.range(offset, end_offset).execute().data or []
            rows.extend(chunk)
            if len(chunk) < resolved_batch_size:
                break
            offset += resolved_batch_size
        return rows

    def _rows_to_payloads(
        self,
        rows: list[dict[str, Any]],
        date_field: str | None = None,
        region_field: str | None = None,
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row.get("payload") or {})
            if date_field and row.get(date_field) and not payload.get(date_field):
                payload[date_field] = row.get(date_field)
            if region_field and row.get(region_field) and not payload.get("c_region"):
                payload["c_region"] = [row.get(region_field)]
            payloads.append(payload)
        return payloads

    def _build_event_attendee_records(self, attendee_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        event_attendee_records: dict[str, list[dict[str, Any]]] = {}
        for row in attendee_rows:
            payload = dict(row.get("payload") or {})
            event_id = payload.get("event_id") or row.get("event_id")
            person_id = payload.get("person_id") or row.get("person_id")
            if person_id and not payload.get("person_id"):
                payload["person_id"] = person_id
            if event_id and not payload.get("event_id"):
                payload["event_id"] = event_id
            if row.get("created_at") and not payload.get("created_at"):
                payload["created_at"] = row.get("created_at")
            if not event_id:
                continue
            event_attendee_records.setdefault(str(event_id), []).append(payload)
            normalized_event_id = self._entity_ref_key(event_id)
            if normalized_event_id and normalized_event_id != str(event_id):
                event_attendee_records.setdefault(normalized_event_id, []).append(payload)
        return event_attendee_records

    def _compute_kpis(
        self,
        region: str,
        people: list[dict[str, Any]],
        organisations: list[dict[str, Any]],
        events: list[dict[str, Any]],
        payments: list[dict[str, Any]],
        grants: list[dict[str, Any]],
        event_attendee_records: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        event_attendee_records = event_attendee_records or {}

        def get_region_tags(record: dict[str, Any]) -> list[Any]:
            return self._to_list(record.get("c_region"))

        def is_in_region(record: dict[str, Any]) -> bool:
            if region == "Global":
                return True
            tags = get_region_tags(record)
            if not tags and record.get("region"):
                tags = self._to_list(record.get("region"))
            return any(region.lower() in str(tag).lower() for tag in tags)

        region_people = [person for person in people if is_in_region(person)]

        volunteers = []
        for person in region_people:
            person_types = [str(value).lower() for value in self._to_list(person.get("type"))]
            if any("volunteer" in person_type for person_type in person_types):
                volunteers.append(person)

        steering_volunteers = []
        for volunteer in volunteers:
            volunteer_types = [str(value).lower() for value in self._to_list(volunteer.get("type"))]
            if any("steering" in value or "committee" in value for value in volunteer_types):
                steering_volunteers.append(volunteer)
        steering_group_proxy = len(steering_volunteers) if steering_volunteers else len(volunteers)

        region_orgs = [organisation for organisation in organisations if is_in_region(organisation)]
        all_orgs = list(organisations or [])
        org_id_to_region = {organisation.get("id"): True for organisation in region_orgs if organisation.get("id") is not None}

        lsp_counts: dict[str, int] = {}
        ldp_counts: dict[str, int] = {}
        corporate_orgs: list[dict[str, Any]] = []

        for org in region_orgs:
            org_type = str(org.get("type") or "").strip()
            if not org_type:
                continue
            if any(token in org_type.lower() for token in ["university", "trust", "political", "parliamentary", "media", "nhs", "prescriber"]):
                lsp_counts[org_type] = lsp_counts.get(org_type, 0) + 1
            else:
                ldp_counts[org_type] = ldp_counts.get(org_type, 0) + 1

        for org in all_orgs:
            org_type = str(org.get("type") or "").strip().lower()
            if "business" in org_type or "corporate" in org_type:
                corporate_orgs.append(org)

        global_grants = []
        for grant in grants:
            org_link = grant.get("organization")
            linked_id = None
            if isinstance(org_link, dict):
                linked_id = org_link.get("id")
            elif isinstance(org_link, str):
                linked_id = org_link

            if linked_id and linked_id in org_id_to_region:
                global_grants.append(grant)
            elif region == "Global":
                global_grants.append(grant)

        if region != "Global":
            global_grants = list(grants or [])

        bids_submitted = sum(
            1 for grant in global_grants if any(token in str(grant.get("stage")).lower() for token in ["submitted", "review", "pending"])
        )
        funds_raised_grants = sum(
            self._coerce_money(grant.get("amount")) for grant in global_grants if str(grant.get("stage")).lower() == "won"
        )

        global_payments = [payment for payment in payments if region == "Global" or is_in_region(payment)]
        if region != "Global":
            global_payments = list(payments or [])
        total_payments = sum(self._coerce_money(payment.get("amount")) for payment in global_payments)
        total_funds = funds_raised_grants + total_payments

        region_events = [event for event in events if is_in_region(event)]

        people_name_by_id: dict[str, str] = {}
        for person in people:
            person_id = person.get("id")
            if person_id is None:
                continue
            person_name = self._get_row_value(person, "name", "full_name", "Display Name", "email") or person_id
            people_name_by_id[self._entity_ref_key(person_id)] = str(person_name).strip()

        walks_delivered = 0
        participants = 0
        event_type_counts: dict[str, int] = {}
        for event in region_events:
            event_type = self._event_type(event)
            if any(token in event_type for token in ["walk", "retreat", "delivery", "session", "hike", "trek"]):
                walks_delivered += 1
                participant_list, participant_ids = self._extract_participant_refs(event, people_name_by_id)
                event_participants = max(self._event_attendees(event), len(participant_list), len(participant_ids))
                participants += event_participants
                event_type_label = event_type.title() if event_type else "Unknown Event Type"
                event_type_counts[event_type_label] = event_type_counts.get(event_type_label, 0) + 1

        if walks_delivered == 0 and region_events:
            walks_delivered = len(region_events)
            participants = sum(self._event_attendees(event) for event in region_events)

        attendee_gender_demographics: dict[str, int] = {}
        seen_attendees: set[str] = set()
        for event in region_events:
            event_id = str(event.get("id") or "")
            attendee_rows = event_attendee_records.get(event_id) or event_attendee_records.get(self._entity_ref_key(event_id)) or []
            for attendee in attendee_rows:
                attendee_key = str(
                    attendee.get("id")
                    or f"{event_id}:{attendee.get('person_id') or attendee.get('name') or attendee.get('email') or ''}"
                ).strip()
                if attendee_key in seen_attendees:
                    continue
                seen_attendees.add(attendee_key)
                label = self._normalize_gender(self._get_row_value(attendee, "c_gender", "Gender", "gender"))
                attendee_gender_demographics[label] = attendee_gender_demographics.get(label, 0) + 1

        if attendee_gender_demographics:
            demographics = attendee_gender_demographics
            demographics_source = "event_attendee_gender"
        elif event_type_counts:
            demographics = event_type_counts
            demographics_source = "event_type_split"
        else:
            demographics = {"General": participants if participants > 0 else 1}
            demographics_source = "fallback"

        return {
            "region": region,
            "last_updated": datetime.now().strftime("%H:%M:%S"),
            "governance": {
                "steering_group_active": steering_group_proxy > 0,
                "steering_members": steering_group_proxy,
                "volunteers_new": len(volunteers),
            },
            "partnerships": {
                "LSP": lsp_counts if lsp_counts else {"None": 0},
                "LDP": ldp_counts if ldp_counts else {"None": 0},
                "active_referrals": len(region_orgs),
                "networks_sat_on": 0,
            },
            "delivery": {
                "walks_delivered": walks_delivered,
                "participants": participants,
                "bursary_participants": 0,
                "wellbeing_change_score": 0,
                "demographics": demographics,
                "demographics_source": demographics_source,
            },
            "income": {
                "bids_submitted": bids_submitted,
                "total_funds_raised": total_funds,
                "corporate_partners": len(corporate_orgs),
                "in_kind_value": 0,
            },
            "_raw_kpi": {
                "region_people": region_people,
                "region_orgs": region_orgs,
                "delivery_events": [
                    {
                        "id": event.get("id"),
                        "name": self._get_row_value(event, "name", "title", "Event name", "Description") or event.get("id"),
                        "type": self._event_type(event),
                        "participants": max(self._event_attendees(event), len(self._extract_participant_refs(event, people_name_by_id)[0])),
                        "date": event.get("start_date") or event.get("date") or event.get("created_at"),
                        "region": ", ".join(str(value) for value in self._to_list(event.get("c_region"))),
                        "participant_list": self._extract_participant_refs(event, people_name_by_id)[0],
                        "participant_ids": self._extract_participant_refs(event, people_name_by_id)[1],
                        "attendee_records": event_attendee_records.get(str(event.get("id") or "")) or event_attendee_records.get(self._entity_ref_key(event.get("id"))) or [],
                        "raw_event": event,
                    }
                    for event in region_events
                ],
                "region_grants": global_grants,
                "region_payments": global_payments,
            },
        }

    def _extract_participant_refs(
        self,
        event_row: dict[str, Any],
        people_name_by_id: dict[str, str],
    ) -> tuple[list[str], list[str]]:
        participant_keys = (
            "participant_list",
            "participants_list",
            "participants",
            "attendees",
            "attendee_list",
            "attendees_list",
            "people",
            "participant_names",
            "attendee_names",
            "contacts",
            "relationships",
        )
        found_names: list[str] = []
        found_ids: list[str] = []
        seen_names: set[str] = set()
        seen_ids: set[str] = set()
        context_tokens = ("participant", "attendee", "people", "contact", "person", "member")
        id_keys = ("id", "person_id", "contact_id", "participant_id", "attendee_id")

        def add_name(value: Any) -> None:
            candidate = str(value).strip()
            if not candidate:
                return
            normalized = candidate.lower()
            if normalized in seen_names:
                return
            seen_names.add(normalized)
            found_names.append(candidate)

        def add_id(value: Any) -> None:
            candidate = str(value).strip()
            if not candidate or candidate in seen_ids:
                return
            seen_ids.add(candidate)
            found_ids.append(candidate)

        def in_context(path: str) -> bool:
            path_lower = path.lower()
            return any(token in path_lower for token in context_tokens)

        def walk(value: Any, path: str = "") -> None:
            if value is None:
                return
            if isinstance(value, dict):
                local_name = value.get("name") or value.get("full_name") or value.get("display_name")
                if local_name:
                    add_name(local_name)
                if value.get("email"):
                    add_name(value.get("email"))
                for id_key in id_keys:
                    if value.get(id_key) is not None and in_context(path):
                        add_id(value.get(id_key))
                for key, nested_value in value.items():
                    next_path = f"{path}.{key}" if path else str(key)
                    walk(nested_value, next_path)
                return
            if isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
                return
            if isinstance(value, str) and in_context(path):
                for token in value.replace("\n", ",").replace(";", ",").split(","):
                    if token.strip():
                        add_name(token.strip())

        for key in participant_keys:
            walk(event_row.get(key), key)

        for person_id in found_ids:
            mapped_name = people_name_by_id.get(self._entity_ref_key(person_id))
            if mapped_name:
                add_name(mapped_name)
        return found_names, found_ids

    def _event_type(self, event_row: dict[str, Any]) -> str:
        for key in ("type", "Type", "Event type", "Activity type", "Category"):
            value = event_row.get(key)
            if value is not None and str(value).strip():
                return str(value).lower()
        return ""

    def _event_attendees(self, event_row: dict[str, Any]) -> int:
        for key in (
            "number_of_attendees",
            "Number of attendees",
            "Attendees",
            "Participants",
            "Total participants",
            "Participant count",
            "Number attending",
        ):
            value = event_row.get(key)
            if value is None or not str(value).strip():
                continue
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                for count_key in ("count", "total", "value", "participants", "attendees"):
                    if value.get(count_key) is not None and str(value.get(count_key)).strip():
                        return self._coerce_int(value.get(count_key))
            return self._coerce_int(value)
        return 0

    def _format_mapping(self, value: dict[str, Any]) -> str:
        if not value:
            return "None"
        return ", ".join(f"{key}: {value[key]}" for key in sorted(value))

    def _get_row_value(self, row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if row.get(key) is not None and str(row.get(key)).strip():
                return row.get(key)
        return None

    def _pretty_field_name(self, name: str) -> str:
        return str(name).replace("_", " ").strip().title()

    def _norm_key(self, value: Any) -> str:
        return "".join(ch for ch in str(value or "").lower() if ch.isalnum())

    def _extract_funder_name(self, row: dict[str, Any]) -> str:
        for key in ("organization_name", "organisation_name", "funder_name", "organization", "organisation", "name"):
            value = row.get(key)
            if isinstance(value, dict):
                nested = value.get("name") or value.get("title") or value.get("id")
                if nested:
                    return str(nested).strip()
            if value not in (None, ""):
                return str(value).strip()
        return "Unknown / Not tagged"

    def _format_currency(self, value: Any) -> str:
        return f"GBP {self._coerce_money(value):,.0f}"

    def _to_iso_boundary(self, value: str | None, is_end: bool) -> str | None:
        if not value:
            return None
        suffix = "T23:59:59" if is_end else "T00:00:00"
        return f"{value}{suffix}"

    def _to_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _coerce_money(self, value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(
                str(value)
                .replace(",", "")
                .replace("GBP", "")
                .replace("????", "")
                .replace("??", "")
                .replace("?", "")
                .strip()
                or 0
            )
        except ValueError:
            return 0.0

    def _coerce_int(self, value: Any) -> int:
        if value is None:
            return 0
        try:
            return int(float(str(value).replace(",", "").strip() or 0))
        except ValueError:
            return 0

    def _normalize_gender(self, value: Any) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return "Unknown"
        if "female" in raw or raw == "f" or "woman" in raw:
            return "Women"
        if "male" in raw or raw == "m" or "man" in raw:
            return "Men"
        return str(value).strip().title()

    def _rows_from_mapping(self, mapping: dict[str, Any], prefix: str) -> list[DashboardDetailRow]:
        rows: list[DashboardDetailRow] = []
        for index, (key, value) in enumerate(mapping.items()):
            if value in (None, "", [], {}):
                continue
            rows.append(DashboardDetailRow(id=f"{prefix}-{index}", label=key, value=str(value)))
        return rows

    def _collect_keyword_rows(self, sources: list[dict[str, Any]], keywords: tuple[str, ...]) -> list[DashboardDetailRow]:
        rows: list[DashboardDetailRow] = []
        seen: set[str] = set()
        for record in sources:
            if not isinstance(record, dict):
                continue
            for key, value in record.items():
                if value in (None, "", [], {}):
                    continue
                key_lower = str(key).lower()
                if any(term in key_lower for term in keywords):
                    label = self._pretty_field_name(key)
                    identity = f"{label}:{value}"
                    if identity in seen:
                        continue
                    seen.add(identity)
                    rows.append(DashboardDetailRow(id=f"{label}-{len(rows)}", label=label, value=str(value)))
        return rows

    def _month_bucket(self, value: Any) -> str | None:
        if not value:
            return None
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text).strftime("%Y-%m")
        except ValueError:
            return None

    def _entity_ref_key(self, value: Any) -> str:
        if value is None:
            return ""
        normalized = str(value).strip().lower()
        if not normalized:
            return ""
        if "/" in normalized:
            normalized = normalized.rstrip("/").split("/")[-1]
        if ":" in normalized:
            normalized = normalized.split(":")[-1]
        digits = "".join(character for character in normalized if character.isdigit())
        if len(digits) >= 4:
            return digits
        return "".join(character for character in normalized if character.isalnum())
