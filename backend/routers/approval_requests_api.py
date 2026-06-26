from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
)
from backend.services.approval_service import (
    approve_approval_request,
    create_approval_request,
    get_approval_request,
    list_approval_requests,
    reject_approval_request,
)


router = APIRouter(prefix="/api/approval-requests", tags=["approval requests"])


@router.post(
    "",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    payload: ApprovalRequestCreate, db: Session = Depends(get_db)
) -> ApprovalRequestResponse:
    return create_approval_request(db, payload)


@router.get("", response_model=list[ApprovalRequestResponse])
def list_requests(db: Session = Depends(get_db)) -> list[ApprovalRequestResponse]:
    return list_approval_requests(db)


@router.get("/{approval_request_id}", response_model=ApprovalRequestResponse)
def get_request(
    approval_request_id: int, db: Session = Depends(get_db)
) -> ApprovalRequestResponse:
    return get_approval_request(db, approval_request_id)


@router.post("/{approval_request_id}/approve", response_model=ApprovalRequestResponse)
def approve_request(
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
) -> ApprovalRequestResponse:
    return approve_approval_request(db, approval_request_id, payload)


@router.post("/{approval_request_id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
) -> ApprovalRequestResponse:
    return reject_approval_request(db, approval_request_id, payload)
