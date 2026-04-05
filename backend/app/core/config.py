from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RPL KPI API"
    environment: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])
    allowed_hosts: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    force_https: bool = False
    enable_api_docs: bool | None = None
    log_level: str = "INFO"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    beacon_api_key: str = ""
    beacon_account_id: str = ""
    beacon_base_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RPL_", extra="ignore")

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def _parse_list_value(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("Expected a JSON list.")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in raw.split(",") if item.strip()]
        raise ValueError("Expected a list or string value.")

    @property
    def api_docs_enabled(self) -> bool:
        if self.enable_api_docs is not None:
            return self.enable_api_docs
        return self.environment.lower() != "production"

    @property
    def missing_core_settings(self) -> list[str]:
        missing: list[str] = []
        if not self.supabase_url:
            missing.append("RPL_SUPABASE_URL")
        if not self.supabase_key:
            missing.append("RPL_SUPABASE_KEY")
        return missing

    @property
    def missing_admin_settings(self) -> list[str]:
        missing: list[str] = []
        if not self.supabase_service_role_key:
            missing.append("RPL_SUPABASE_SERVICE_ROLE_KEY")
        return missing

    @property
    def missing_sync_settings(self) -> list[str]:
        missing: list[str] = []
        if not self.beacon_api_key:
            missing.append("RPL_BEACON_API_KEY")
        if not self.beacon_account_id and not self.beacon_base_url:
            missing.append("RPL_BEACON_ACCOUNT_ID or RPL_BEACON_BASE_URL")
        if not self.supabase_service_role_key:
            missing.append("RPL_SUPABASE_SERVICE_ROLE_KEY")
        return missing


settings = Settings()
