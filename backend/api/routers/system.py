from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db, require_minimum_role
from backend.api.errors import ApiError
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.system import HealthResponse, ReadinessResponse, SystemStatusResponse

router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/health/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)) -> ReadinessResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise ApiError(503, "service_not_ready", "Database readiness check failed") from error
    return ReadinessResponse(status="ready")


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status(
    request: Request,
    _: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> SystemStatusResponse:
    summary = request.app.state.settings.safe_summary()
    return SystemStatusResponse(**summary)
