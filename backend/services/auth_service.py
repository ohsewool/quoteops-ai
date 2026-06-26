from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
SESSION_HOURS = 12
ADMIN_ROLES = {"owner", "manager", "viewer"}


class AuthError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class AuthUnauthorizedError(AuthError):
    status_code = 401


class AuthForbiddenError(AuthError):
    status_code = 403


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_text() -> str:
    return _utc_now().isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return (
        f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}$"
        f"{salt.hex()}${password_hash.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, hash_hex = stored_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False
    if algorithm != PASSWORD_ALGORITHM:
        return False

    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate_hash, hash_hex)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def admin_to_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def login_admin(
    connection: sqlite3.Connection,
    *,
    email: str,
    password: str,
) -> dict[str, Any]:
    admin = connection.execute(
        """
        SELECT id, email, display_name, role, password_hash, is_active, created_at
        FROM admin_users
        WHERE LOWER(email) = LOWER(?)
        """,
        (email.strip(),),
    ).fetchone()
    if admin is None or not admin["is_active"]:
        raise AuthUnauthorizedError("Invalid admin email or password.")
    if not verify_password(password, admin["password_hash"]):
        raise AuthUnauthorizedError("Invalid admin email or password.")

    token = secrets.token_urlsafe(32)
    now = _utc_now()
    expires_at = now + timedelta(hours=SESSION_HOURS)
    connection.execute(
        """
        INSERT INTO admin_sessions (
            admin_user_id, token_hash, created_at, expires_at, revoked_at
        )
        VALUES (?, ?, ?, ?, NULL)
        """,
        (
            admin["id"],
            token_hash(token),
            now.isoformat(),
            expires_at.isoformat(),
        ),
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": admin_to_public(admin),
    }


def get_admin_from_token(
    connection: sqlite3.Connection,
    *,
    token: str,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            au.id, au.email, au.display_name, au.role, au.is_active, au.created_at,
            s.expires_at, s.revoked_at
        FROM admin_sessions s
        JOIN admin_users au ON au.id = s.admin_user_id
        WHERE s.token_hash = ?
        """,
        (token_hash(token),),
    ).fetchone()
    if row is None or row["revoked_at"] is not None or not row["is_active"]:
        raise AuthUnauthorizedError("Admin session is invalid or expired.")
    if _parse_datetime(row["expires_at"]) <= _utc_now():
        raise AuthUnauthorizedError("Admin session is invalid or expired.")
    return admin_to_public(row)


def logout_admin(
    connection: sqlite3.Connection,
    *,
    token: str,
) -> dict[str, str]:
    connection.execute(
        """
        UPDATE admin_sessions
        SET revoked_at = ?
        WHERE token_hash = ? AND revoked_at IS NULL
        """,
        (_utc_now_text(), token_hash(token)),
    )
    return {"status": "ok", "message": "Admin session logged out."}


def require_role(admin: dict[str, Any], allowed_roles: set[str]) -> None:
    if admin["role"] not in allowed_roles:
        raise AuthForbiddenError("This admin role is not allowed to perform this action.")
