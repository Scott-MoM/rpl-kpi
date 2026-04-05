from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSession(BaseModel):
    email: EmailStr
    name: str
    role: str
    roles: list[str]
    region: str
    force_password_change: bool = False


class LoginResponse(BaseModel):
    user: UserSession
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    email: EmailStr
    temporary_password: str
    new_password: str


class PasswordResetRequestCreate(BaseModel):
    email: EmailStr
