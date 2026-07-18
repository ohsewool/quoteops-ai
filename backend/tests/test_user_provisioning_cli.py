from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from backend.cli import create_user
from backend.cli.user_provisioning import (
    normalize_display_name,
    normalize_username,
    require_v2_application_database,
    resolve_password,
)
from backend.domain.roles import UserRole


def test_usernames_are_normalized_and_reject_unsafe_values() -> None:
    assert normalize_username(" Review.Admin ") == "review.admin"
    with pytest.raises(SystemExit, match="Username must be"):
        normalize_username("two words")


def test_display_names_are_trimmed_and_bounded() -> None:
    assert normalize_display_name(" Review Admin ") == "Review Admin"
    with pytest.raises(SystemExit, match="Display name must"):
        normalize_display_name(" ")


def test_password_environment_input_uses_review_prefix_without_echoing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUOTEOPS_REVIEW_ADMIN_PASSWORD", "sufficiently-long-test-password")
    args = argparse.Namespace(password=None, password_env="QUOTEOPS_REVIEW_ADMIN_PASSWORD")

    assert resolve_password(args) == "sufficiently-long-test-password"

    with pytest.raises(SystemExit, match="QUOTEOPS_REVIEW_"):
        resolve_password(argparse.Namespace(password=None, password_env="QUOTEOPS_AUTH_SECRET"))


def test_missing_password_environment_value_fails_without_revealing_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.cli.user_provisioning._password_from_ignored_env", lambda _name: None)

    with pytest.raises(SystemExit, match="QUOTEOPS_REVIEW_MISSING_PASSWORD"):
        resolve_password(argparse.Namespace(password=None, password_env="QUOTEOPS_REVIEW_MISSING_PASSWORD"))


def test_user_provisioning_refuses_a_test_database_target() -> None:
    settings = SimpleNamespace(
        database_is_configured=True,
        auth_secret=SecretStr("configured-test-secret"),
        database_url="postgresql+psycopg://review:password@localhost:5432/quoteops_ai_v2_test",
    )

    with pytest.raises(SystemExit, match="application database"):
        require_v2_application_database(settings)


def test_subsequent_user_cli_requires_admin_actor_and_records_safe_audit_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = SimpleNamespace(id=7, active=True, role=UserRole.ADMIN)
    created = SimpleNamespace(id=11)
    session = SimpleNamespace(committed=False, rolled_back=False, closed=False)
    audit_calls: list[dict[str, object]] = []

    class FakeRepository:
        def __init__(self, _session: object) -> None:
            pass

        def user_count(self) -> int:
            return 1

        def get_by_username(self, username: str) -> object | None:
            return actor if username == "review-admin" else None

        def create(self, **_kwargs: object) -> object:
            return created

    def commit() -> None:
        session.committed = True

    def rollback() -> None:
        session.rolled_back = True

    def close() -> None:
        session.closed = True

    session.commit = commit
    session.rollback = rollback
    session.close = close
    monkeypatch.setattr(
        create_user,
        "parse_args",
        lambda: argparse.Namespace(
            actor_username="review-admin",
            username="review-manager-1",
            display_name="Review Manager 1",
            role="manager",
            password=None,
            password_env="QUOTEOPS_REVIEW_MANAGER_1_PASSWORD",
        ),
    )
    monkeypatch.setattr(create_user, "Settings", lambda: SimpleNamespace())
    monkeypatch.setattr(create_user, "require_v2_application_database", lambda _settings: None)
    monkeypatch.setattr(create_user, "resolve_password", lambda _args: "sufficiently-long-test-password")
    monkeypatch.setattr(create_user, "hash_password", lambda _password: "safe-test-hash")
    monkeypatch.setattr(create_user, "build_session_factory", lambda _settings: lambda: session)
    monkeypatch.setattr(create_user, "SqlAlchemyUserRepository", FakeRepository)
    monkeypatch.setattr(
        create_user,
        "append_audit_event",
        lambda _session, **kwargs: audit_calls.append(kwargs),
    )

    assert create_user.main() == 0
    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True
    assert len(audit_calls) == 1
    audit_call = audit_calls[0]
    assert audit_call["actor_user_id"] == 7
    assert audit_call["action"] == "user.provisioned"
    assert audit_call["entity_type"] == "user"
    assert audit_call["entity_id"] == "11"
    assert isinstance(audit_call["request_id"], str)
    assert audit_call["metadata"] == {"role": "manager", "provisioned_by_cli": True}
    assert "password" not in str(audit_calls)
