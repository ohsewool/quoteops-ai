from fastapi import APIRouter, Depends, Header, HTTPException, Request

from backend.db import get_connection
from backend.routers.auth_api import require_admin_roles, require_manager_or_owner_admin
from backend.schemas.approval import ApprovalActionResponse, ApprovalRequest
from backend.schemas.candidate import CandidateGenerateRequest, CandidateGenerateResponse
from backend.schemas.explanation import CandidateExplanationResponse
from backend.schemas.validation import CandidateValidationResponse
from backend.services.approval_service import (
    ApprovalError,
    approve_candidate_table,
    reject_candidate_table,
)
from backend.services.audit_logger import audit_actor, log_audit_event
from backend.services.auth_service import AuthError
from backend.services.candidate_generator import (
    CandidateGenerationError,
    generate_candidate_prices,
)
from backend.services.candidate_validator import (
    CandidateValidationError,
    validate_candidate_table,
)
from backend.services.explanation_service import ExplanationError, explain_candidate_table

router = APIRouter(prefix="/api/candidate-prices", tags=["candidate-prices"])


@router.post("/generate", response_model=CandidateGenerateResponse)
def generate_candidate_price_table(
    request: CandidateGenerateRequest,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            result = generate_candidate_prices(
                connection,
                product_id=request.product_id,
                product_slug=request.product_slug,
                option_summary=request.option_summary,
                quantities=request.quantities,
                strategy_name=request.strategy_name,
                strategy_template_id=request.strategy_template_id,
            )
            log_audit_event(
                connection,
                action="candidate_table_generated",
                entity_type="candidate_table",
                entity_id=result["candidate_table_id"],
                entity_label=result["candidate_table_name"],
                after={
                    "candidate_table_id": result["candidate_table_id"],
                    "product_id": result["product_id"],
                    "strategy_name": result["strategy_name"],
                    "strategy_template_id": request.strategy_template_id,
                    "status": result["status"],
                    "item_count": result["summary"]["item_count"],
                },
            )
            return result
    except CandidateGenerationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{candidate_table_id}/validate", response_model=CandidateValidationResponse)
def validate_candidate_price_table(
    candidate_table_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            result = validate_candidate_table(
                connection,
                candidate_table_id=candidate_table_id,
            )
            log_audit_event(
                connection,
                action="candidate_table_validated",
                entity_type="validation_result",
                entity_id=result["validation_result_id"],
                entity_label=result["candidate_table_name"],
                after={
                    "candidate_table_id": candidate_table_id,
                    "overall_status": result["overall_status"],
                    "risk_level": result["risk_level"],
                    "summary": result["summary"],
                },
            )
            return result
    except CandidateValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{candidate_table_id}/explain", response_model=CandidateExplanationResponse)
def explain_candidate_price_table(
    candidate_table_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            result = explain_candidate_table(
                connection,
                candidate_table_id=candidate_table_id,
            )
            log_audit_event(
                connection,
                action="ai_explanation_generated",
                entity_type="ai_explanation",
                entity_id=candidate_table_id,
                entity_label=f"Candidate table #{candidate_table_id}",
                after={
                    "candidate_table_id": candidate_table_id,
                    "source": result["source"],
                    "warnings": result["warnings"],
                },
            )
            return result
    except ExplanationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{candidate_table_id}/approve", response_model=ApprovalActionResponse)
def approve_candidate_price_table(
    candidate_table_id: int,
    request: ApprovalRequest,
    http_request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        admin = require_admin_roles(
            authorization,
            {"owner"},
            request=http_request,
            action="candidate_table_approve",
        )
        with get_connection() as connection:
            result = approve_candidate_table(
                connection,
                candidate_table_id=candidate_table_id,
                reviewer_name=admin["display_name"],
                reviewer_note=request.reviewer_note,
            )
            actor = audit_actor(admin)
            log_audit_event(
                connection,
                action="candidate_table_approved",
                entity_type="candidate_table",
                entity_id=candidate_table_id,
                entity_label=f"Candidate table #{candidate_table_id}",
                after=result,
                **actor,
            )
            log_audit_event(
                connection,
                action="price_table_activated",
                entity_type="price_table",
                entity_id=result["created_price_table_id"],
                entity_label=f"Approved price table #{result['created_price_table_id']}",
                metadata={
                    "candidate_table_id": candidate_table_id,
                    "approval_id": result["approval_id"],
                },
                **actor,
            )
            return result
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{candidate_table_id}/reject", response_model=ApprovalActionResponse)
def reject_candidate_price_table(
    candidate_table_id: int,
    request: ApprovalRequest,
    http_request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    try:
        admin = require_admin_roles(
            authorization,
            {"owner"},
            request=http_request,
            action="candidate_table_reject",
        )
        with get_connection() as connection:
            result = reject_candidate_table(
                connection,
                candidate_table_id=candidate_table_id,
                reviewer_name=admin["display_name"],
                reviewer_note=request.reviewer_note,
            )
            log_audit_event(
                connection,
                action="candidate_table_rejected",
                entity_type="candidate_table",
                entity_id=candidate_table_id,
                entity_label=f"Candidate table #{candidate_table_id}",
                after=result,
                **audit_actor(admin),
            )
            return result
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ApprovalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
