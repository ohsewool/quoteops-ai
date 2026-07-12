from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user, get_settings, get_user_repository
from backend.api.errors import ApiError
from backend.config import Settings
from backend.models.user import User
from backend.repositories.users import UserRepository
from backend.schemas.auth import LoginRequest, LoginResponse, UserResponse
from backend.services.passwords import verify_password
from backend.services.tokens import TokenConfigurationError, issue_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    repository: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = repository.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "invalid_credentials", "Invalid username or password")
    if not user.active:
        raise ApiError(403, "inactive_user", "This user is inactive")
    try:
        token, expires_at = issue_access_token(user, settings)
    except TokenConfigurationError as error:
        raise ApiError(503, "authentication_unavailable", "Authentication is unavailable") from error
    return LoginResponse(access_token=token, expires_at=expires_at, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def current_user(current: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current)
