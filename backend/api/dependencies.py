from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.config import Settings
from backend.db import SessionFactory
from backend.domain.roles import UserRole, has_minimum_role
from backend.models.user import User
from backend.repositories.users import SqlAlchemyUserRepository, UserRepository
from backend.services.tokens import TokenValidationError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory: SessionFactory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    repository: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "authentication_required", "Authentication is required")
    try:
        claims = decode_access_token(credentials.credentials, settings)
    except TokenValidationError as error:
        raise ApiError(401, "invalid_access_token", "Authentication is invalid or expired") from error

    user = repository.get_active_by_id(claims.user_id)
    if user is None:
        raise ApiError(401, "inactive_or_missing_user", "Authentication is invalid or inactive")
    return user


def require_minimum_role(required: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_minimum_role(current_user.role, required):
            raise ApiError(403, "permission_denied", "Insufficient role for this operation")
        return current_user

    return dependency
