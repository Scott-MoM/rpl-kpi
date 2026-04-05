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

from app.services.admin_service import AdminService


class FakeQuery:
    def __init__(self, data):
        self.data = data

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name: str):
        assert name == "user_roles"
        return FakeQuery(self.rows)


def test_list_users_prefers_admin_client(monkeypatch) -> None:
    public_rows = []
    admin_rows = [
        {"name": "Alice Admin", "email": "alice@example.com", "region": "North", "roles": {"name": "Admin"}},
        {"name": "Alice Admin", "email": "alice@example.com", "region": "North", "roles": {"name": "Manager"}},
    ]

    monkeypatch.setattr("app.services.admin_service.get_supabase_client", lambda: FakeClient(public_rows))
    monkeypatch.setattr("app.services.admin_service.get_supabase_admin_client", lambda: FakeClient(admin_rows))

    users = AdminService().list_users()

    assert len(users) == 1
    assert users[0].email == "alice@example.com"
    assert users[0].role == "Admin, Manager"
    assert users[0].region == "North"
