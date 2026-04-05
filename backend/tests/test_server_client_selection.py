from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
while str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))

from app.db import supabase


def test_server_client_prefers_admin_client(monkeypatch) -> None:
    admin_client = object()
    public_client = object()

    monkeypatch.setattr(supabase, "get_supabase_admin_client", lambda: admin_client)
    monkeypatch.setattr(supabase, "get_supabase_client", lambda: public_client)

    assert supabase.get_supabase_server_client() is admin_client


def test_server_client_falls_back_to_public_client(monkeypatch) -> None:
    public_client = object()

    monkeypatch.setattr(supabase, "get_supabase_admin_client", lambda: None)
    monkeypatch.setattr(supabase, "get_supabase_client", lambda: public_client)

    assert supabase.get_supabase_server_client() is public_client
