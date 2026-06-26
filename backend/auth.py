import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Iterable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User


ALLOWED_ROLES = {"admin", "manager", "viewer"}
ROLE_LEVELS = {"viewer": 1, "manager": 2, "admin": 3}
TOKEN_TTL_SECONDS = 60 * 60 * 8
security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), resolved_salt.encode("utf-8"), 120_000
    ).hex()
    return f"pbkdf2_sha256$120000${resolved_salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(digest, expected_digest)


def create_access_token(user: User) -> str:
    issued_at = int(time.time())
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "issued_at": issued_at,
        "expires_at": issued_at + TOKEN_TTL_SECONDS,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        payload = json.loads(_b64decode(encoded_payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if int(payload.get("expires_at", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, payload.get("user_id"))
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except HTTPException:
        return None
    user = db.get(User, payload.get("user_id"))
    if user is None or not user.active:
        return None
    return user


def require_any_role(roles: Iterable[str]):
    allowed = set(roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current_user

    return dependency


def require_role(minimum_role: str):
    if minimum_role not in ROLE_LEVELS:
        raise ValueError(f"Unsupported role: {minimum_role}")

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVELS[current_user.role] < ROLE_LEVELS[minimum_role]:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current_user

    return dependency


def _sign(encoded_payload: str) -> str:
    digest = hmac.new(
        _auth_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _auth_secret() -> str:
    # Development fallback is intentionally unsafe for production.
    return os.getenv("QUOTEOPS_AUTH_SECRET", "dev-only-quoteops-auth-secret")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
