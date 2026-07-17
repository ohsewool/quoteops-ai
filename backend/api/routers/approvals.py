"""Authenticated approval request and decision HTTP adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, get_settings, require_minimum_role
from backend.api.errors import ApiError
from backend.config import Settings
from backend.domain.approvals import ApprovalStatus
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.approvals import (
    ApprovalDecisionRequest,
    ApprovalRequestCreate,
    ApprovalRequestPageResponse,
    ApprovalRequestResponse,
)
from backend.services.approvals import (
    create_approval_request,
    decide_approval_request,
    get_approval_request,
    list_approval_requests,
)


router = APIRouter(prefix="/api", tags=["approvals"])


def _request_id(request: Request) -> str:
    return request.state.request_id


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(422, "invalid_pagination", "Page must be positive and page size must be between 1 and 100")


@router.get("/approval-requests", response_model=ApprovalRequestPageResponse)
def approval_request_list(
    page: int = 1,
    page_size: int = 25,
    status_filter: ApprovalStatus | None = None,
    quote_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ApprovalRequestPageResponse:
    _validate_pagination(page, page_size)
    return list_approval_requests(
        db,
        page=page,
        page_size=page_size,
        status=status_filter,
        quote_id=quote_id,
    )


@router.post(
    "/approval-requests",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def approval_request_create(
    payload: ApprovalRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> ApprovalRequestResponse:
    return create_approval_request(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/approval-requests/{approval_request_id}", response_model=ApprovalRequestResponse)
def approval_request_detail(
    approval_request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ApprovalRequestResponse:
    return get_approval_request(db, approval_request_id)


@router.post("/approval-requests/{approval_request_id}/approve", response_model=ApprovalRequestResponse)
def approval_request_approve(
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> ApprovalRequestResponse:
    return decide_approval_request(
        db,
        approval_request_id=approval_request_id,
        payload=payload,
        actor=actor,
        decision=ApprovalStatus.APPROVED,
        settings=settings,
        request_id=_request_id(request),
    )


@router.post("/approval-requests/{approval_request_id}/reject", response_model=ApprovalRequestResponse)
def approval_request_reject(
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> ApprovalRequestResponse:
    return decide_approval_request(
        db,
        approval_request_id=approval_request_id,
        payload=payload,
        actor=actor,
        decision=ApprovalStatus.REJECTED,
        settings=settings,
        request_id=_request_id(request),
    )
