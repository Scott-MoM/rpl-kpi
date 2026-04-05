from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
while str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))

from app.services.auth_service import AuthService


class FakeAuthApi:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email

    def get_user(self, _access_token: str):
        return SimpleNamespace(user=SimpleNamespace(id=self.user_id, email=self.email))


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class FakeClient:
    def __init__(self, rows, user_id: str = "user-1", email: str = "admin@example.com"):
        self._rows = rows
        self.auth = FakeAuthApi(user_id, email)

    def table(self, name: str):
        assert name == "user_roles"
        return FakeQuery(self._rows)


def test_get_current_user_prefers_server_client_for_roles(monkeypatch) -> None:
    public_client = FakeClient([])
    server_client = FakeClient(
        [
            {"region": "North", "name": "Alice Admin", "must_change_password": False, "roles": {"name": "Admin"}},
            {"region": "North", "name": "Alice Admin", "must_change_password": False, "roles": {"name": "Manager"}},
        ]
    )

    monkeypatch.setattr("app.services.auth_service.get_supabase_client", lambda: public_client)
    monkeypatch.setattr("app.services.auth_service.get_supabase_server_client", lambda: server_client)

    user = AuthService().get_current_user("token")

    assert user.name == "Alice Admin"
    assert user.role == "Admin"
    assert user.roles == ["Admin", "Manager"]
    assert user.region == "North"
