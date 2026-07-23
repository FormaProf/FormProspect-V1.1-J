import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_production_rejects_sqlite_and_missing_supabase_configuration():
    with pytest.raises(ValidationError):
        Settings(environment="production", database_url="sqlite+pysqlite:///prod.db")


def test_production_rejects_local_test_secret():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://localhost/formaprospect",
            supabase_url="https://example.supabase.co",
            supabase_jwt_issuer="https://example.supabase.co/auth/v1",
            supabase_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
            local_test_jwt_secret="forbidden",
        )

