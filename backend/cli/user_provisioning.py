"""Shared safeguards for explicit local user-provisioning commands."""

from __future__ import annotations

import argparse
import getpass
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

from backend.config import Settings


_PASSWORD_ENV_PREFIX = "QUOTEOPS_REVIEW_"
_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def add_password_arguments(parser: argparse.ArgumentParser) -> None:
    """Add non-echoing password input choices without changing startup behavior."""

    password_group = parser.add_mutually_exclusive_group()
    password_group.add_argument("--password", help="Avoid this option in shared shell history.")
    password_group.add_argument(
        "--password-env",
        metavar="ENV_VAR",
        help="Read a password from an ignored QUOTEOPS_REVIEW_* environment variable.",
    )


def normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(username):
        raise SystemExit("Username must be 3-64 lowercase letters, digits, dots, underscores, or hyphens.")
    return username


def normalize_display_name(value: str) -> str:
    display_name = value.strip()
    if not display_name or len(display_name) > 128:
        raise SystemExit("Display name must contain 1-128 characters.")
    return display_name


def _password_from_ignored_env(variable_name: str) -> str | None:
    value = os.getenv(variable_name)
    if value is not None:
        return value
    return dotenv_values(Path(".env")).get(variable_name)


def resolve_password(args: argparse.Namespace) -> str:
    """Resolve a password without printing it or adding it to an audit event."""

    password_env = getattr(args, "password_env", None)
    if password_env:
        if not password_env.startswith(_PASSWORD_ENV_PREFIX):
            raise SystemExit("Password environment variables must use the QUOTEOPS_REVIEW_ prefix.")
        password = _password_from_ignored_env(password_env)
        if not password:
            raise SystemExit(f"Password environment variable {password_env} is not configured.")
        return password

    password = getattr(args, "password", None)
    if password is None:
        password = getpass.getpass("Password: ")
    if not password:
        raise SystemExit("A non-empty password is required.")
    return password


def require_v2_application_database(settings: Settings) -> None:
    """Reject an accidental test-database invocation without exposing a URL."""

    if not settings.database_is_configured:
        raise SystemExit("A V2-only PostgreSQL application database must be configured before creating a user.")
    if settings.auth_secret is None or settings.auth_secret.get_secret_value().startswith("CHANGE_ME"):
        raise SystemExit("A configured V2 authentication secret is required before creating a user.")
    normalized_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    database_name = urlsplit(normalized_url).path.rsplit("/", 1)[-1].lower()
    if database_name.endswith("_test"):
        raise SystemExit("User provisioning must target the V2 application database, not the test database.")
