from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.db.supabase import get_supabase_admin_client, get_supabase_client
from app.core.config import settings
from app.schemas.admin import (
    AdminOverview,
    AuditLogEntry,
    AdminUser,
    CsvImportSummary,
    DeleteUserRequest,
    CompleteResetRequest,
    CreateUserRequest,
    PendingPasswordReset,
    ResetPasswordRequest,
    SyncPerformanceSummary,
    UpdateUserRequest,
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sync_beacon_to_supabase import log_system_audit, upsert_rows


class AdminService:
    _role_choices = {"RPL", "ML", "Manager", "Admin", "Funder"}

    def get_overview(self) -> AdminOverview:
        admin_client = get_supabase_admin_client()
        client = admin_client or get_supabase_client()
        if not client:
            return AdminOverview(
                title="Admin Dashboard",
                pending_password_resets=0,
                user_count=0,
                last_refresh=None,
                data_source="unconfigured",
                sync_supported=False,
                core_configured=not settings.missing_core_settings,
                admin_configured=not settings.missing_admin_settings,
                sync_configured=not settings.missing_sync_settings,
                core_missing=settings.missing_core_settings,
                admin_missing=settings.missing_admin_settings,
                sync_missing=settings.missing_sync_settings,
            )

        user_rows = client.table("user_roles").select("email").execute().data or []
        unique_users = {str(row.get("email") or "").strip().lower() for row in user_rows if row.get("email")}

        pending_password_resets = len(self.list_pending_password_resets()) if admin_client else 0
        last_refresh = None
        for table_name, date_field in (
            ("beacon_events", "start_date"),
            ("beacon_payments", "payment_date"),
            ("beacon_grants", "close_date"),
            ("beacon_people", "created_at"),
        ):
            try:
                row = client.table(table_name).select(date_field).order(date_field, desc=True).limit(1).execute().data or []
            except Exception:
                row = []
            if row and row[0].get(date_field):
                last_refresh = str(row[0][date_field])
                break

        return AdminOverview(
            title="Admin Dashboard",
            pending_password_resets=pending_password_resets,
            user_count=len(unique_users),
            last_refresh=last_refresh,
            data_source="supabase",
            sync_supported=bool(admin_client),
            core_configured=not settings.missing_core_settings,
            admin_configured=not settings.missing_admin_settings,
            sync_configured=not settings.missing_sync_settings,
            core_missing=settings.missing_core_settings,
            admin_missing=settings.missing_admin_settings,
            sync_missing=settings.missing_sync_settings,
        )

    def list_users(self) -> list[AdminUser]:
        client = self._admin_read_client()
        response = client.table("user_roles").select("name, email, region, roles(name)").execute()
        users_map: dict[str, dict] = {}
        for row in response.data or []:
            email = str(row.get("email") or "").strip().lower()
            if not email:
                continue
            entry = users_map.setdefault(
                email,
                {"name": row.get("name"), "email": email, "roles": set(), "region": row.get("region")},
            )
            role_name = (row.get("roles") or {}).get("name")
            if role_name:
                entry["roles"].add(role_name)
            if row.get("name") and not entry.get("name"):
                entry["name"] = row.get("name")
            if row.get("region"):
                entry["region"] = row.get("region")

        return [
            AdminUser(
                name=entry.get("name"),
                email=entry["email"],
                role=", ".join(sorted(entry["roles"])) if entry["roles"] else "RPL",
                region=entry.get("region"),
            )
            for entry in users_map.values()
        ]

    def list_pending_password_resets(self) -> list[PendingPasswordReset]:
        admin_client = self._admin_client()
        try:
            rows = (
                admin_client.table("password_reset_requests")
                .select("id, email, status, created_at")
                .eq("status", "pending")
                .order("created_at", desc=True)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        return [PendingPasswordReset(**row) for row in rows]

    def create_user(self, payload: CreateUserRequest) -> AdminUser:
        admin_client = self._admin_client()
        roles = self._normalize_roles(payload.roles)
        if not roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one role is required.")

        user_response = admin_client.auth.admin.create_user(
            {"email": payload.email.strip().lower(), "password": payload.password, "email_confirm": True}
        )
        user_id = user_response.user.id

        inserted_roles: list[str] = []
        for role_name in roles:
            role_response = admin_client.table("roles").select("id").eq("name", role_name).execute()
            if not role_response.data:
                continue
            role_id = role_response.data[0]["id"]
            admin_client.table("user_roles").insert(
                {
                    "user_id": user_id,
                    "role_id": role_id,
                    "region": payload.region,
                    "email": payload.email.strip().lower(),
                    "name": payload.name,
                    "must_change_password": True,
                }
            ).execute()
            inserted_roles.append(role_name)

        if not inserted_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role lookup failed.")

        return AdminUser(name=payload.name, email=payload.email.strip().lower(), role=", ".join(inserted_roles), region=payload.region)

    def update_user(self, email: str, payload: UpdateUserRequest) -> AdminUser:
        admin_client = self._admin_client()
        normalized_email = email.strip().lower()
        roles = self._normalize_roles(payload.roles)
        if not payload.confirmed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role change must be confirmed.")
        if not payload.reason.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A reason is required for the role update.")
        if not roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one role is required.")

        role_response = (
            admin_client.table("user_roles").select("user_id, name").eq("email", normalized_email).limit(1).execute()
        )
        if not role_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user_id = role_response.data[0]["user_id"]
        current_name = role_response.data[0].get("name")
        admin_client.table("user_roles").delete().eq("email", normalized_email).execute()

        inserted_roles: list[str] = []
        for role_name in roles:
            role_lookup = admin_client.table("roles").select("id").eq("name", role_name).limit(1).execute()
            if not role_lookup.data:
                continue
            admin_client.table("user_roles").insert(
                {
                    "user_id": user_id,
                    "role_id": role_lookup.data[0]["id"],
                    "region": payload.region,
                    "email": normalized_email,
                    "name": current_name,
                    "must_change_password": False,
                }
            ).execute()
            inserted_roles.append(role_name)

        if not inserted_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role lookup failed.")

        log_system_audit(
            admin_client,
            "User Role Updated",
            {
                "target_email": normalized_email,
                "roles": inserted_roles,
                "region": payload.region,
                "reason": payload.reason.strip(),
                "confirmed": True,
            },
            region=payload.region or "Global",
        )

        return AdminUser(
            name=current_name,
            email=normalized_email,
            role=", ".join(inserted_roles),
            region=payload.region,
        )

    def reset_password(self, payload: ResetPasswordRequest) -> dict[str, str]:
        admin_client = self._admin_client()
        role_response = admin_client.table("user_roles").select("user_id").eq("email", payload.email.strip().lower()).execute()
        if not role_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        user_id = role_response.data[0]["user_id"]
        admin_client.auth.admin.update_user_by_id(user_id, {"password": payload.new_password})
        return {"status": "updated"}

    def complete_password_reset_request(self, payload: CompleteResetRequest) -> dict[str, str]:
        admin_client = self._admin_client()
        role_response = admin_client.table("user_roles").select("user_id").eq("email", payload.email.strip().lower()).execute()
        if not role_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        user_id = role_response.data[0]["user_id"]
        admin_client.auth.admin.update_user_by_id(user_id, {"password": payload.temporary_password})
        admin_client.table("user_roles").update({"must_change_password": True}).eq("user_id", user_id).execute()
        admin_client.table("password_reset_requests").update({"status": "completed"}).eq("email", payload.email.strip().lower()).execute()
        return {"status": "completed"}

    def delete_user(self, email: str, payload: DeleteUserRequest) -> dict[str, str]:
        admin_client = self._admin_client()
        normalized_email = email.strip().lower()
        if not payload.confirmed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User deletion must be confirmed.")
        if not payload.reason.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A reason is required for deletion.")

        role_response = admin_client.table("user_roles").select("user_id, region").eq("email", normalized_email).execute()
        if not role_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        user_id = role_response.data[0]["user_id"]
        region = role_response.data[0].get("region") or "Global"
        admin_client.table("user_roles").delete().eq("email", normalized_email).execute()
        admin_client.auth.admin.delete_user(user_id)
        log_system_audit(
            admin_client,
            "User Deleted",
            {"target_email": normalized_email, "reason": payload.reason.strip(), "confirmed": True},
            region=region,
        )
        return {"status": "deleted"}

    def list_audit_logs(self, search: str | None = None, action: str | None = None, limit: int = 200) -> list[AuditLogEntry]:
        client = self._admin_read_client()
        try:
            rows = client.table("audit_logs").select("created_at, user_email, action, region, details").order("created_at", desc=True).limit(limit).execute().data or []
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        search_term = (search or "").strip().lower()
        action_filter = (action or "").strip()
        filtered: list[AuditLogEntry] = []
        for row in rows:
            current_action = str(row.get("action") or "")
            if action_filter and current_action != action_filter:
                continue
            details = row.get("details")
            details_text = json.dumps(details, sort_keys=True, default=str) if isinstance(details, (dict, list)) else str(details or "")
            haystack = " ".join(
                [
                    str(row.get("user_email") or ""),
                    current_action,
                    str(row.get("region") or ""),
                    details_text,
                ]
            ).lower()
            if search_term and search_term not in haystack:
                continue
            filtered.append(AuditLogEntry(**row))
        return filtered

    def get_sync_performance(self) -> SyncPerformanceSummary:
        client = self._admin_read_client()
        try:
            rows = (
                client.table("audit_logs")
                .select("created_at, action, details")
                .in_("action", ["Data Sync Completed", "Data Sync Failed"])
                .order("created_at", desc=True)
                .limit(100)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        completed = []
        for row in rows:
            if row.get("action") != "Data Sync Completed":
                continue
            details = row.get("details") or {}
            if details.get("source") != "beacon_api":
                continue
            completed.append({"created_at": row.get("created_at"), "details": details})

        if not completed:
            return SyncPerformanceSummary()

        latest = completed[0]
        latest_details = latest.get("details") or {}
        recent = completed[:10]
        average_total = sum(int((item.get("details") or {}).get("total_duration_ms") or 0) for item in recent) / len(recent)
        return SyncPerformanceSummary(
            latest_total_ms=int(latest_details.get("total_duration_ms") or 0),
            latest_fetch_ms=int(latest_details.get("fetch_duration_ms") or 0),
            latest_transform_ms=int(latest_details.get("transform_duration_ms") or 0),
            latest_upsert_ms=int(latest_details.get("upsert_duration_ms") or 0),
            average_total_ms=float(average_total),
            recent_success_count=len(recent),
            last_success_at=latest.get("created_at"),
            last_sync_type="Automatic" if latest_details.get("trigger") == "github_actions" else "Manual",
        )

    async def import_beacon_csvs(
        self,
        people_file: UploadFile | None = None,
        organisation_file: UploadFile | None = None,
        event_file: UploadFile | None = None,
        payment_file: UploadFile | None = None,
        grant_file: UploadFile | None = None,
    ) -> CsvImportSummary:
        admin_client = self._admin_client()
        uploads = {
            "people": await self._read_upload_rows(people_file),
            "organization": await self._read_upload_rows(organisation_file),
            "event": await self._read_upload_rows(event_file),
            "payment": await self._read_upload_rows(payment_file),
            "grant": await self._read_upload_rows(grant_file),
        }

        people_rows = [self._norm_people(row) for row in uploads["people"] if row.get("Record ID")]
        org_rows = [self._norm_org(row) for row in uploads["organization"] if row.get("Record ID")]
        event_rows = [self._norm_event(row) for row in uploads["event"] if row.get("Record ID")]
        payment_rows = [self._norm_payment(row) for row in uploads["payment"] if row.get("Record ID")]
        grant_rows = [self._norm_grant(row) for row in uploads["grant"] if row.get("Record ID")]

        try:
            result = CsvImportSummary(
                people=upsert_rows(
                    "beacon_people",
                    [{"id": row.get("id"), "payload": row, "created_at": row.get("created_at")} for row in people_rows],
                    admin_client,
                ),
                organisations=upsert_rows(
                    "beacon_organisations",
                    [{"id": row.get("id"), "payload": row, "created_at": row.get("created_at")} for row in org_rows],
                    admin_client,
                ),
                events=upsert_rows(
                    "beacon_events",
                    [
                        {
                            "id": row.get("id"),
                            "payload": row,
                            "start_date": row.get("start_date"),
                            "region": (row.get("c_region") or [None])[0],
                        }
                        for row in event_rows
                    ],
                    admin_client,
                ),
                payments=upsert_rows(
                    "beacon_payments",
                    [{"id": row.get("id"), "payload": row, "payment_date": row.get("payment_date")} for row in payment_rows],
                    admin_client,
                ),
                grants=upsert_rows(
                    "beacon_grants",
                    [{"id": row.get("id"), "payload": row, "close_date": row.get("close_date")} for row in grant_rows],
                    admin_client,
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        log_system_audit(
            admin_client,
            "Data Imported",
            {"source": "beacon_csv", **result.model_dump()},
            region="Global",
        )
        return result

    async def _read_upload_rows(self, upload: UploadFile | None) -> list[dict[str, str]]:
        if upload is None:
            return []
        content = await upload.read()
        if not content:
            return []
        text = content.decode("utf-8-sig", errors="ignore")
        sample = text[:2048]
        try:
            delimiter = csv.Sniffer().sniff(sample).delimiter
        except Exception:
            delimiter = ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return [dict(row) for row in reader]

    def _norm_people(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["id"] = row.get("Record ID")
        payload["created_at"] = self._clean_ts(row.get("Created date"))
        payload["type"] = self._to_list(row.get("Type"))
        payload["c_region"] = self._to_list(row.get("Region"))
        return payload

    def _norm_org(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["id"] = row.get("Record ID")
        payload["created_at"] = self._clean_ts(row.get("Created date"))
        payload["type"] = row.get("Type")
        payload["c_region"] = self._to_list(row.get("Region"))
        return payload

    def _norm_event(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["id"] = row.get("Record ID")
        payload["start_date"] = self._clean_ts(row.get("Start date"))
        payload["type"] = row.get("Type")
        payload["c_region"] = self._to_list(row.get("Location (region)"))
        payload["number_of_attendees"] = row.get("Number of attendees")
        return payload

    def _norm_payment(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["id"] = row.get("Record ID")
        payload["payment_date"] = self._clean_ts(row.get("Payment date"))
        payload["amount"] = row.get("Amount (value)")
        return payload

    def _norm_grant(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["id"] = row.get("Record ID")
        payload["close_date"] = self._clean_ts(row.get("Award date"))
        payload["amount"] = row.get("Amount granted (value)") or row.get("Amount requested (value)") or row.get("Value (value)")
        payload["stage"] = row.get("Stage")
        return payload

    def _clean_ts(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _to_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        text = str(value).strip()
        if not text:
            return []
        parts = [part.strip() for part in text.split(",") if part.strip()]
        return parts if parts else [text]

    def _normalize_roles(self, roles: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for role in roles:
            value = str(role).strip()
            if not value or value not in self._role_choices or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _client(self):
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )
        return client

    def _admin_read_client(self):
        return get_supabase_admin_client() or self._client()

    def _admin_client(self):
        admin_client = get_supabase_admin_client()
        if not admin_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role is not configured.",
            )
        return admin_client
