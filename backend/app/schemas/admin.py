from pydantic import BaseModel


class AdminOverview(BaseModel):
    title: str
    pending_password_resets: int
    user_count: int
    last_refresh: str | None = None
    data_source: str = "unavailable"
    sync_supported: bool = False


class SyncJobState(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    user_email: str | None = None
    region: str | None = None
    started_at: float | None = None
    ended_at: float | None = None
    error: str | None = None


class StartSyncRequest(BaseModel):
    user_email: str = "System"
    region: str = "Global"


class AdminUser(BaseModel):
    name: str | None = None
    email: str
    role: str
    region: str | None = None


class PendingPasswordReset(BaseModel):
    id: str | None = None
    email: str
    status: str
    created_at: str | None = None


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    roles: list[str]
    region: str


class UpdateUserRequest(BaseModel):
    roles: list[str]
    region: str
    reason: str
    confirmed: bool = False


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


class CompleteResetRequest(BaseModel):
    email: str
    temporary_password: str


class DeleteUserRequest(BaseModel):
    reason: str
    confirmed: bool = False


class AuditLogEntry(BaseModel):
    created_at: str | None = None
    user_email: str | None = None
    action: str
    region: str | None = None
    details: dict | list | str | None = None


class SyncPerformanceSummary(BaseModel):
    latest_total_ms: int = 0
    latest_fetch_ms: int = 0
    latest_transform_ms: int = 0
    latest_upsert_ms: int = 0
    average_total_ms: float = 0
    recent_success_count: int = 0
    last_success_at: str | None = None
    last_sync_type: str | None = None


class CsvImportSummary(BaseModel):
    people: int = 0
    organisations: int = 0
    events: int = 0
    payments: int = 0
    grants: int = 0
