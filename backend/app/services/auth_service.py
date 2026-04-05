from fastapi import HTTPException, status

from ..db.supabase import get_supabase_admin_client, get_supabase_client, get_supabase_server_client
from ..schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, PasswordResetRequestCreate, UserSession


class AuthService:
    def login(self, payload: LoginRequest) -> LoginResponse:
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        try:
            auth_response = client.auth.sign_in_with_password(
                {"email": str(payload.email).strip().lower(), "password": payload.password}
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        if not auth_response or not auth_response.user or not auth_response.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login credentials.")

        user = self._build_user_session(auth_response.user.id, str(auth_response.user.email or payload.email))
        return LoginResponse(user=user, access_token=auth_response.session.access_token)

    def change_password(self, payload: ChangePasswordRequest) -> None:
        client = get_supabase_client()
        admin_client = get_supabase_admin_client()
        if not client or not admin_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password change requires Supabase client and service role configuration.",
            )

        try:
            auth_response = client.auth.sign_in_with_password(
                {"email": str(payload.email).strip().lower(), "password": payload.temporary_password}
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Temporary password is incorrect.") from exc

        if not auth_response or not auth_response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Temporary password is incorrect.")

        admin_client.auth.admin.update_user_by_id(auth_response.user.id, {"password": payload.new_password})
        admin_client.table("user_roles").update({"must_change_password": False}).eq("user_id", auth_response.user.id).execute()

    def request_password_reset(self, payload: PasswordResetRequestCreate) -> dict[str, str]:
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        email = str(payload.email).strip().lower()
        try:
            existing = (
                client.table("password_reset_requests")
                .select("id")
                .eq("email", email)
                .eq("status", "pending")
                .limit(1)
                .execute()
            )
            if existing.data:
                return {"status": "pending"}
            client.table("password_reset_requests").insert({"email": email, "status": "pending"}).execute()
            return {"status": "created"}
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    def get_current_user(self, access_token: str) -> UserSession:
        client = get_supabase_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )

        try:
            user_response = client.auth.get_user(access_token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.") from exc

        if not user_response or not user_response.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token.")

        email = str(user_response.user.email or "").strip().lower()
        return self._build_user_session(user_response.user.id, email)

    def _build_user_session(self, user_id: str, fallback_email: str) -> UserSession:
        client = get_supabase_server_client()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase is not configured. Set RPL_SUPABASE_URL and RPL_SUPABASE_KEY.",
            )
        try:
            role_response = (
                client.table("user_roles")
                .select("region, name, must_change_password, roles(name)")
                .eq("user_id", user_id)
                .execute()
            )
            rows = role_response.data or []
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load user roles: {exc}",
            ) from exc

        role_names: list[str] = []
        display_name = fallback_email
        region = "Global"
        must_change_password = False

        for row in rows:
            role_name = (row.get("roles") or {}).get("name")
            if role_name and role_name not in role_names:
                role_names.append(role_name)
            row_name = str(row.get("name") or "").strip()
            row_region = str(row.get("region") or "").strip()
            if row_name and display_name == fallback_email:
                display_name = row_name
            if row_region and region == "Global":
                region = row_region
            if row.get("must_change_password"):
                must_change_password = True

        if not role_names:
            role_names = ["RPL"]

        return UserSession(
            email=fallback_email,
            name=display_name,
            role=role_names[0],
            roles=role_names,
            region=region,
            force_password_change=must_change_password,
        )
