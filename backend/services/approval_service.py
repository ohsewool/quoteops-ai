from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import PriceApprovalRequest
from backend.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    PriceValidationRequest,
)
from backend.services.validation_service import validate_price


WORKFLOW_NOTES = [
    "Approval request created for human review.",
    "No AI approval decision was used.",
    "This request does not activate a price table item.",
]


def create_approval_request(
    db: Session, payload: ApprovalRequestCreate
) -> ApprovalRequestResponse:
    validation = validate_price(
        db,
        PriceValidationRequest(
            product_id=payload.product_id,
            quantity=payload.quantity,
            candidate_unit_price=payload.proposed_unit_price,
            minimum_margin_rate=payload.minimum_margin_rate,
        ),
    )
    approval_request = PriceApprovalRequest(
        product_id=validation.product_id,
        quantity=validation.quantity,
        proposed_unit_price=validation.candidate_unit_price,
        proposed_total_price=validation.candidate_total_price,
        unit_cost=validation.unit_cost,
        total_cost=validation.total_cost,
        estimated_gross_profit=validation.estimated_gross_profit,
        estimated_margin_rate=validation.estimated_margin_rate,
        minimum_margin_rate=validation.minimum_margin_rate,
        validation_status=validation.validation_status,
        risk_level=validation.risk_level,
        status="pending",
        submitted_note=payload.submitted_note,
    )
    db.add(approval_request)
    db.commit()
    db.refresh(approval_request)
    return _to_response(approval_request)


def list_approval_requests(db: Session) -> list[ApprovalRequestResponse]:
    requests = db.query(PriceApprovalRequest).order_by(PriceApprovalRequest.id).all()
    return [_to_response(approval_request) for approval_request in requests]


def get_approval_request(
    db: Session, approval_request_id: int
) -> ApprovalRequestResponse:
    approval_request = _get_model(db, approval_request_id)
    return _to_response(approval_request)


def approve_approval_request(
    db: Session,
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
) -> ApprovalRequestResponse:
    approval_request = _get_pending_model(db, approval_request_id)
    approval_request.status = "approved"
    approval_request.reviewer_name = payload.reviewer_name
    approval_request.review_note = payload.review_note
    approval_request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(approval_request)
    return _to_response(approval_request)


def reject_approval_request(
    db: Session,
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
) -> ApprovalRequestResponse:
    approval_request = _get_pending_model(db, approval_request_id)
    approval_request.status = "rejected"
    approval_request.reviewer_name = payload.reviewer_name
    approval_request.review_note = payload.review_note
    approval_request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(approval_request)
    return _to_response(approval_request)


def _get_model(db: Session, approval_request_id: int) -> PriceApprovalRequest:
    approval_request = db.get(PriceApprovalRequest, approval_request_id)
    if approval_request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval_request


def _get_pending_model(db: Session, approval_request_id: int) -> PriceApprovalRequest:
    approval_request = _get_model(db, approval_request_id)
    if approval_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending approval requests can be reviewed",
        )
    return approval_request


def _to_response(approval_request: PriceApprovalRequest) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=approval_request.id,
        product_id=approval_request.product_id,
        product_name=approval_request.product.name,
        quantity=approval_request.quantity,
        proposed_unit_price=approval_request.proposed_unit_price,
        proposed_total_price=approval_request.proposed_total_price,
        unit_cost=approval_request.unit_cost,
        total_cost=approval_request.total_cost,
        estimated_gross_profit=approval_request.estimated_gross_profit,
        estimated_margin_rate=approval_request.estimated_margin_rate,
        minimum_margin_rate=approval_request.minimum_margin_rate,
        validation_status=approval_request.validation_status,
        risk_level=approval_request.risk_level,
        status=approval_request.status,
        submitted_note=approval_request.submitted_note,
        reviewer_name=approval_request.reviewer_name,
        review_note=approval_request.review_note,
        created_at=approval_request.created_at,
        updated_at=approval_request.updated_at,
        reviewed_at=approval_request.reviewed_at,
        workflow_notes=WORKFLOW_NOTES,
    )
