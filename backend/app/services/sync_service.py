from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

from fastapi import HTTPException, status

from ..core.config import settings
from ..db.supabase import get_supabase_admin_client, get_supabase_client
from ..schemas.admin import StartSyncRequest, SyncJobState

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sync_beacon_to_supabase import log_system_audit, run_sync_once


class SyncService:
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="beacon-sync")
    _lock = threading.Lock()
    _jobs: dict[str, dict] = {}

    def start_manual_sync(self, payload: StartSyncRequest) -> SyncJobState:
        self._ensure_sync_config()
        existing = self._find_running_job(payload.user_email)
        if existing:
            return SyncJobState(**existing)

        job_id = uuid.uuid4().hex[:10]
        state = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "Queued...",
            "created_at": time.time(),
            "user_email": payload.user_email,
            "region": payload.region,
        }
        with self._lock:
            self._jobs[job_id] = state
        self._executor.submit(self._run_manual_sync_job, job_id)
        return SyncJobState(**state)

    def stop_job(self, job_id: str, user_email: str = "System", region: str = "Global") -> SyncJobState:
        with self._lock:
            state = self._jobs.get(job_id)
            if not state:
                recovered = self.get_job(job_id)
                if recovered.status in ("completed", "failed", "cancelled"):
                    return recovered
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual sync job not found.")
            if state.get("status") == "queued":
                state.update(
                    {
                        "status": "cancelled",
                        "progress": 100,
                        "message": "Manual sync cancelled before start.",
                        "ended_at": time.time(),
                    }
                )
            elif state.get("status") not in ("completed", "failed", "cancelled"):
                state["cancel_requested"] = True
                state["message"] = "Cancellation requested..."
            self._jobs[job_id] = state

        admin_client = get_supabase_admin_client()
        if admin_client:
            log_system_audit(
                admin_client,
                "Data Sync Cancellation Requested",
                {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
                region=region,
                user_email=user_email,
            )
        return SyncJobState(**state)

    def clear_job(self, job_id: str, user_email: str = "System", region: str = "Global") -> SyncJobState:
        with self._lock:
            state = self._jobs.get(job_id, {"job_id": job_id, "user_email": user_email, "region": region})
            state.update(
                {
                    "status": "cancelled",
                    "progress": 100,
                    "message": "Manual sync cleared by user.",
                    "ended_at": time.time(),
                }
            )
            self._jobs[job_id] = state

        admin_client = get_supabase_admin_client()
        if admin_client:
            log_system_audit(
                admin_client,
                "Data Sync Cleared",
                {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
                region=region,
                user_email=user_email,
            )
        return SyncJobState(**state)

    def get_job(self, job_id: str) -> SyncJobState:
        with self._lock:
            state = self._jobs.get(job_id)
            if state:
                return SyncJobState(**state)

        recovered = self._get_latest_manual_sync_state()
        if recovered and recovered.get("job_id") == job_id:
            return SyncJobState(**recovered)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual sync job not found.")

    def get_latest_job(self, user_email: str | None = None) -> SyncJobState | None:
        with self._lock:
            candidates = []
            for state in self._jobs.values():
                if user_email and state.get("user_email") not in (user_email, "System"):
                    continue
                ts = state.get("created_at") or state.get("started_at") or 0
                candidates.append((ts, state))
            if candidates:
                candidates.sort(key=lambda item: item[0], reverse=True)
                return SyncJobState(**candidates[0][1])

        recovered = self._get_latest_manual_sync_state(user_email=user_email)
        return SyncJobState(**recovered) if recovered else None

    def _run_manual_sync_job(self, job_id: str) -> None:
        state = self._get_state(job_id)
        user_email = state.get("user_email", "System")
        region = state.get("region", "Global")

        if state.get("status") == "cancelled" or state.get("cancel_requested"):
            self._set_state(
                job_id,
                status="cancelled",
                progress=100,
                message="Manual sync cancelled before start.",
                ended_at=time.time(),
            )
            return

        started_at = time.time()
        self._set_state(job_id, status="running", progress=0, message="Starting Beacon API sync...", started_at=started_at)

        admin_client = get_supabase_admin_client()
        if not admin_client:
            self._set_state(
                job_id,
                status="failed",
                progress=100,
                message="Supabase service role is not configured.",
                ended_at=time.time(),
                error="Supabase service role is not configured.",
            )
            return

        log_system_audit(
            admin_client,
            "Data Sync Started",
            {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
            region=region,
            user_email=user_email,
        )

        try:
            self._set_state(job_id, progress=10, message="Fetching Beacon entities...")
            summary = run_sync_once(
                admin_client,
                settings.beacon_api_key,
                settings.beacon_account_id,
                settings.beacon_base_url,
            )
            result = {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id, **summary}
            log_system_audit(admin_client, "Data Sync Completed", result, region=region, user_email=user_email)
            self._set_state(
                job_id,
                status="completed",
                progress=100,
                message="Beacon API sync complete.",
                ended_at=time.time(),
            )
        except Exception as exc:
            current = self._get_state(job_id)
            if current.get("cancel_requested"):
                log_system_audit(
                    admin_client,
                    "Data Sync Cancelled",
                    {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id},
                    region=region,
                    user_email=user_email,
                )
                self._set_state(
                    job_id,
                    status="cancelled",
                    progress=100,
                    message="Manual sync cancelled.",
                    ended_at=time.time(),
                )
                return

            log_system_audit(
                admin_client,
                "Data Sync Failed",
                {"source": "beacon_api", "trigger": "manual_ui", "job_id": job_id, "error": str(exc)},
                region=region,
                user_email=user_email,
            )
            self._set_state(
                job_id,
                status="failed",
                progress=100,
                message="Beacon API sync failed.",
                ended_at=time.time(),
                error=str(exc),
            )

    def _ensure_sync_config(self) -> None:
        if not settings.beacon_api_key:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RPL_BEACON_API_KEY is not configured.")
        if not settings.beacon_base_url and not settings.beacon_account_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Set RPL_BEACON_BASE_URL or RPL_BEACON_ACCOUNT_ID for Beacon sync.",
            )
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase service role configuration is required for sync.",
            )

    def _set_state(self, job_id: str, **updates) -> dict:
        with self._lock:
            state = self._jobs.get(job_id, {"job_id": job_id})
            state.update(updates)
            self._jobs[job_id] = state
            return dict(state)

    def _get_state(self, job_id: str) -> dict:
        with self._lock:
            return dict(self._jobs.get(job_id) or {})

    def _find_running_job(self, user_email: str | None = None) -> dict | None:
        with self._lock:
            for state in self._jobs.values():
                if user_email and state.get("user_email") not in (user_email, "System"):
                    continue
                if state.get("status") in ("queued", "running"):
                    return dict(state)
        recovered = self._get_latest_manual_sync_state(user_email=user_email)
        if recovered and recovered.get("status") == "running":
            return recovered
        return None

    def _get_latest_manual_sync_state(self, user_email: str | None = None, lookback_rows: int = 300) -> dict | None:
        client = get_supabase_client()
        if not client:
            return None
        try:
            rows = (
                client.table("audit_logs")
                .select("created_at, user_email, action, details, region")
                .in_(
                    "action",
                    [
                        "Data Sync Started",
                        "Data Sync Progress",
                        "Data Sync Completed",
                        "Data Sync Failed",
                        "Data Sync Cancelled",
                        "Data Sync Cleared",
                    ],
                )
                .order("created_at", desc=True)
                .limit(lookback_rows)
                .execute()
                .data
                or []
            )
        except Exception:
            return None

        filtered = []
        for row in rows:
            details = row.get("details") or {}
            if details.get("source") != "beacon_api" or details.get("trigger") != "manual_ui":
                continue
            if user_email and row.get("user_email") not in (user_email, "System"):
                continue
            if not details.get("job_id"):
                continue
            filtered.append(row)
        if not filtered:
            return None

        latest = filtered[0]
        job_id = (latest.get("details") or {}).get("job_id")
        job_rows = [row for row in filtered if (row.get("details") or {}).get("job_id") == job_id]
        start_row = next((row for row in reversed(job_rows) if row.get("action") == "Data Sync Started"), None)
        end_row = next(
            (
                row
                for row in job_rows
                if row.get("action") in ("Data Sync Completed", "Data Sync Failed", "Data Sync Cancelled", "Data Sync Cleared")
            ),
            None,
        )
        progress_row = next((row for row in job_rows if row.get("action") == "Data Sync Progress"), None)

        status_value = "running"
        if end_row:
            if end_row.get("action") == "Data Sync Completed":
                status_value = "completed"
            elif end_row.get("action") in ("Data Sync Cancelled", "Data Sync Cleared"):
                status_value = "cancelled"
            else:
                status_value = "failed"

        progress = 100 if status_value in ("completed", "failed", "cancelled") else int((progress_row or {}).get("details", {}).get("progress") or 0)
        message = "Starting Beacon API sync..."
        if progress_row:
            message = ((progress_row.get("details") or {}).get("message")) or message
        if status_value == "completed":
            message = "Beacon API sync complete."
        elif status_value == "failed":
            message = "Beacon API sync failed."
        elif status_value == "cancelled":
            message = "Manual sync cleared by user." if end_row and end_row.get("action") == "Data Sync Cleared" else "Beacon API sync cancelled."

        state = {
            "job_id": job_id,
            "status": status_value,
            "progress": progress,
            "message": message,
            "user_email": latest.get("user_email"),
            "region": latest.get("region"),
        }
        if start_row and start_row.get("created_at"):
            state["started_at"] = self._timestamp_from_value(start_row.get("created_at"))
        if end_row and end_row.get("created_at"):
            state["ended_at"] = self._timestamp_from_value(end_row.get("created_at"))
        if end_row and status_value == "failed":
            state["error"] = ((end_row.get("details") or {}).get("error")) or "Beacon API sync failed."
        return state

    def _timestamp_from_value(self, value) -> float | None:
        if value is None:
            return None
        try:
            return time.mktime(time.strptime(str(value).split(".")[0].replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S"))
        except Exception:
            return None
