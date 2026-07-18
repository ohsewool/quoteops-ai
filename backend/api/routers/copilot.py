"""Authenticated routes for immutable, grounded copilot text outputs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, require_minimum_role
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.copilot import GroundedCopilotOutputCreate, GroundedCopilotOutputResponse
from backend.services.copilot import create_grounded_copilot_output, get_grounded_copilot_output


router = APIRouter(prefix="/api", tags=["grounded copilot"])


@router.post(
    "/quotes/{quote_id}/copilot-outputs",
    response_model=GroundedCopilotOutputResponse,
    status_code=status.HTTP_201_CREATED,
)
def copilot_output_create(
    quote_id: int,
    payload: GroundedCopilotOutputCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> GroundedCopilotOutputResponse:
    return create_grounded_copilot_output(
        db,
        quote_id=quote_id,
        payload=payload,
        actor=actor,
        request_id=request.state.request_id,
    )


@router.get("/copilot-outputs/{output_id}", response_model=GroundedCopilotOutputResponse)
def copilot_output_detail(
    output_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> GroundedCopilotOutputResponse:
    return get_grounded_copilot_output(db, output_id)
