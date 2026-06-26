from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import get_optional_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
)
from backend.services.audit_service import create_audit_log
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
    payload: ApprovalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ApprovalRequestResponse:
    response = create_approval_request(db, payload)
    create_audit_log(
        db,
        action="approval_request_created",
        entity_type="approval_request",
        entity_id=response.id,
        summary=f"Approval request {response.id} created.",
        metadata={
            "approval_request_id": response.id,
            "product_id": response.product_id,
            "quantity": response.quantity,
            "proposed_unit_price": response.proposed_unit_price,
            "validation_status": response.validation_status,
        },
        actor=current_user,
    )
    return response


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
    current_user: User | None = Depends(get_optional_current_user),
) -> ApprovalRequestResponse:
    response = approve_approval_request(db, approval_request_id, payload)
    create_audit_log(
        db,
        action="approval_request_approved",
        entity_type="approval_request",
        entity_id=response.id,
        summary=f"Approval request {response.id} approved.",
        metadata={
            "approval_request_id": response.id,
            "product_id": response.product_id,
            "reviewer_name": response.reviewer_name,
            "status": response.status,
        },
        actor=current_user,
    )
    return response


@router.post("/{approval_request_id}/reject", response_model=ApprovalRequestResponse)
def reject_request(
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ApprovalRequestResponse:
    response = reject_approval_request(db, approval_request_id, payload)
    create_audit_log(
        db,
        action="approval_request_rejected",
        entity_type="approval_request",
        entity_id=response.id,
        summary=f"Approval request {response.id} rejected.",
        metadata={
            "approval_request_id": response.id,
            "product_id": response.product_id,
            "reviewer_name": response.reviewer_name,
            "status": response.status,
        },
        actor=current_user,
    )
    return response
