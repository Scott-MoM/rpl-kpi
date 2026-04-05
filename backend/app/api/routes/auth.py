from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, PasswordResetRequestCreate, UserSession
from app.services.auth_service import AuthService

router = APIRouter()
service = AuthService()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    return service.login(payload)


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest) -> dict[str, str]:
    service.change_password(payload)
    return {"status": "accepted"}


@router.post("/password-reset-request")
def request_password_reset(payload: PasswordResetRequestCreate) -> dict[str, str]:
    return service.request_password_reset(payload)


@router.get("/me", response_model=UserSession)
def get_current_user(authorization: str | None = Header(default=None)) -> UserSession:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    return service.get_current_user(authorization.split(" ", 1)[1].strip())
