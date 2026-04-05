from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
while str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))

from app.core.config import settings
from app.main import app


client = TestClient(app)


def test_healthcheck_is_available() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_reports_missing_core_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_key", "")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    monkeypatch.setattr(settings, "beacon_api_key", "")
    monkeypatch.setattr(settings, "beacon_account_id", "")
    monkeypatch.setattr(settings, "beacon_base_url", "")

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["core"]["configured"] is False
    assert "RPL_SUPABASE_URL" in payload["checks"]["core"]["missing"]
    assert "RPL_SUPABASE_KEY" in payload["checks"]["core"]["missing"]


def test_readiness_reports_ready_with_optional_warnings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_key", "public-key")
    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    monkeypatch.setattr(settings, "beacon_api_key", "")
    monkeypatch.setattr(settings, "beacon_account_id", "")
    monkeypatch.setattr(settings, "beacon_base_url", "")

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["core"]["configured"] is True
    assert payload["checks"]["admin"]["configured"] is False
    assert payload["checks"]["sync"]["configured"] is False


def test_auth_me_requires_bearer_token() -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token."
