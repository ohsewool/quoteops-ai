from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import jwt
from jwt import InvalidTokenError

from backend.config import Settings
from backend.domain.roles import UserRole


class TokenSubject(Protocol):
    id: int
    role: UserRole


class TokenConfigurationError(RuntimeError):
    pass


class TokenValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: int
    role: UserRole
    expires_at: datetime


def _signing_secret(settings: Settings) -> str:
    if settings.auth_secret is None:
        raise TokenConfigurationError("Authentication is not configured")
    secret = settings.auth_secret.get_secret_value()
    if not secret or secret.startswith("CHANGE_ME"):
        raise TokenConfigurationError("Authentication is not configured")
    return secret


def issue_access_token(subject: TokenSubject, settings: Settings) -> tuple[str, datetime]:
    # JWT numeric-date claims are second-granularity, so normalize before both
    # signing and returning the expiry contract.
    now = datetime.now(timezone.utc).replace(microsecond=0)
    expires_at = now + timedelta(minutes=settings.auth_token_ttl_minutes)
    token = jwt.encode(
        {
            "sub": str(subject.id),
            "role": subject.role.value,
            "iss": settings.auth_issuer,
            "iat": now,
            "exp": expires_at,
        },
        _signing_secret(settings),
        algorithm="HS256",
    )
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            _signing_secret(settings),
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
        )
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
        return AccessTokenClaims(
            user_id=int(payload["sub"]),
            role=UserRole(payload["role"]),
            expires_at=expires_at,
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise TokenValidationError("Invalid or expired access token") from error
