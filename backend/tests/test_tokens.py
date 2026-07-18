from dataclasses import dataclass

import pytest

from backend.config import Settings
from backend.domain.roles import UserRole
from backend.services.tokens import TokenValidationError, decode_access_token, issue_access_token


@dataclass
class Subject:
    id: int
    role: UserRole


def token_settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://v2:password@localhost:5432/quoteops_v2",
        test_database_url="postgresql+psycopg://v2_test:password@localhost:5432/quoteops_v2_test",
        auth_secret="unit-test-auth-secret",
        auth_token_ttl_minutes=15,
    )


def test_access_token_has_expiry_and_role_claims() -> None:
    token, expires_at = issue_access_token(Subject(7, UserRole.MANAGER), token_settings())
    claims = decode_access_token(token, token_settings())

    assert claims.user_id == 7
    assert claims.role is UserRole.MANAGER
    assert claims.expires_at == expires_at


def test_invalid_access_token_is_not_accepted() -> None:
    with pytest.raises(TokenValidationError, match="Invalid or expired"):
        decode_access_token("not-a-token", token_settings())
