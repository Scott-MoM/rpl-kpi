from fastapi import APIRouter, File, Query, UploadFile

from ...schemas.admin import (
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
    StartSyncRequest,
    SyncJobState,
    UpdateUserRequest,
)
from ...services.admin_service import AdminService
from ...services.sync_service import SyncService

router = APIRouter()
admin_service = AdminService()
sync_service = SyncService()


@router.get("/overview", response_model=AdminOverview)
def get_admin_overview() -> AdminOverview:
    return admin_service.get_overview()


@router.get("/users", response_model=list[AdminUser])
def list_users() -> list[AdminUser]:
    return admin_service.list_users()


@router.post("/users", response_model=AdminUser)
def create_user(payload: CreateUserRequest) -> AdminUser:
    return admin_service.create_user(payload)


@router.patch("/users/{email}", response_model=AdminUser)
def update_user(email: str, payload: UpdateUserRequest) -> AdminUser:
    return admin_service.update_user(email, payload)


@router.delete("/users/{email}")
def delete_user(email: str, payload: DeleteUserRequest) -> dict[str, str]:
    return admin_service.delete_user(email, payload)


@router.post("/users/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict[str, str]:
    return admin_service.reset_password(payload)


@router.get("/password-reset-requests", response_model=list[PendingPasswordReset])
def list_password_reset_requests() -> list[PendingPasswordReset]:
    return admin_service.list_pending_password_resets()


@router.post("/password-reset-requests/complete")
def complete_password_reset_request(payload: CompleteResetRequest) -> dict[str, str]:
    return admin_service.complete_password_reset_request(payload)


@router.get("/sync/performance", response_model=SyncPerformanceSummary)
def get_sync_performance() -> SyncPerformanceSummary:
    return admin_service.get_sync_performance()


@router.get("/audit-logs", response_model=list[AuditLogEntry])
def list_audit_logs(
    search: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AuditLogEntry]:
    return admin_service.list_audit_logs(search=search, action=action, limit=limit)


@router.post("/imports/beacon-csv", response_model=CsvImportSummary)
async def import_beacon_csv(
    people_file: UploadFile | None = File(default=None),
    organisation_file: UploadFile | None = File(default=None),
    event_file: UploadFile | None = File(default=None),
    payment_file: UploadFile | None = File(default=None),
    grant_file: UploadFile | None = File(default=None),
) -> CsvImportSummary:
    return await admin_service.import_beacon_csvs(
        people_file=people_file,
        organisation_file=organisation_file,
        event_file=event_file,
        payment_file=payment_file,
        grant_file=grant_file,
    )


@router.post("/sync", response_model=SyncJobState)
def start_manual_sync(payload: StartSyncRequest) -> SyncJobState:
    return sync_service.start_manual_sync(payload)


@router.get("/sync/latest", response_model=SyncJobState | None)
def get_latest_manual_sync(user_email: str | None = None) -> SyncJobState | None:
    return sync_service.get_latest_job(user_email=user_email)


@router.get("/sync/{job_id}", response_model=SyncJobState)
def get_manual_sync(job_id: str) -> SyncJobState:
    return sync_service.get_job(job_id)


@router.post("/sync/{job_id}/stop", response_model=SyncJobState)
def stop_manual_sync(job_id: str, payload: StartSyncRequest) -> SyncJobState:
    return sync_service.stop_job(job_id, user_email=payload.user_email, region=payload.region)


@router.post("/sync/{job_id}/clear", response_model=SyncJobState)
def clear_manual_sync(job_id: str, payload: StartSyncRequest) -> SyncJobState:
    return sync_service.clear_job(job_id, user_email=payload.user_email, region=payload.region)
