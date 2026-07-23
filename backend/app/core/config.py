from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    app_name: str = "Form@Prospect Cloud API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+pysqlite:///:memory:"
    supabase_url: str = ""
    supabase_jwt_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str = ""
    supabase_service_role_key: str = ""
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    trusted_proxy_count: int = 0
    access_token_leeway_seconds: int = 30
    local_test_jwt_secret: str = ""

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def split_hosts(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.environment == "production":
            required = {
                "supabase_url": self.supabase_url,
                "supabase_jwt_issuer": self.supabase_jwt_issuer,
                "supabase_jwks_url": self.supabase_jwks_url,
                "supabase_service_role_key": self.supabase_service_role_key,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"Configuration de production incomplète: {', '.join(missing)}")
            if self.database_url.startswith("sqlite"):
                raise ValueError("SQLite est interdit pour le backend de production.")
            if self.local_test_jwt_secret:
                raise ValueError("local_test_jwt_secret est interdit en production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
