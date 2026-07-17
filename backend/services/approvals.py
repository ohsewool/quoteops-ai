"""Transactional approval workflow over immutable quote and pricing evidence."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.config import Settings
from backend.domain.approvals import ApprovalStatus
from backend.domain.money import decimal_string, to_decimal
from backend.domain.pricing import PricingCheckStatus, RiskLevel, ValidationStatus
from backend.domain.quotes import QuoteStatus
from backend.models.approval import ApprovalDecision, ApprovalRequest
from backend.models.pricing import (
    PriceCandidate,
    PriceCandidateLine,
    PriceValidationCheck,
    PriceValidationResult,
    PricingCheck,
)
from backend.models.quote import Quote, QuoteRevision
from backend.models.user import User
from backend.repositories.quotes import QuoteRepository
from backend.schemas.approvals import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRequestCreate,
    ApprovalRequestPageResponse,
    ApprovalRequestResponse,
)
from backend.services.audit import append_audit_event
from backend.services.pricing_engine import CandidateValidation, PricingLineInput, calculate_candidate, validate_candidate
from backend.services.quotes import create_workflow_revision


def _flush(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "approval_conflict", "The approval request could not be saved") from error


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "approval_conflict", "The approval request could not be saved") from error


def _decision_for_request(session: Session, approval_request_id: int) -> ApprovalDecision | None:
    return session.scalar(
        select(ApprovalDecision).where(ApprovalDecision.approval_request_id == approval_request_id)
    )


def _response(session: Session, approval_request: ApprovalRequest) -> ApprovalRequestResponse:
    quote = session.scalar(select(Quote).where(Quote.id == approval_request.quote_id))
    if quote is None:
        raise ApiError(409, "approval_quote_missing", "Approval quote lineage is incomplete")
    decision = _decision_for_request(session, approval_request.id)
    decision_response = None
    if decision is not None:
        decision_response = ApprovalDecisionResponse(
            id=decision.id,
            decision=decision.decision,
            reviewer_user_id=decision.reviewer_user_id,
            reason=decision.reason,
            result_quote_revision_id=decision.result_quote_revision_id,
            demo_self_approval_used=decision.demo_self_approval_used,
            created_at=decision.created_at,
        )
    return ApprovalRequestResponse(
        id=approval_request.id,
        quote_id=approval_request.quote_id,
        quote_revision_id=approval_request.quote_revision_id,
        quote_version=approval_request.quote_version,
        pricing_check_id=approval_request.pricing_check_id,
        price_candidate_id=approval_request.price_candidate_id,
        requester_user_id=approval_request.requester_user_id,
        status=approval_request.status,
        quote_current_status=quote.status,
        validation_status=approval_request.validation_status,
        risk_level=approval_request.risk_level,
        currency=approval_request.currency,
        candidate_total_price=decimal_string(approval_request.candidate_total_price),
        candidate_gross_profit=decimal_string(approval_request.candidate_gross_profit),
        candidate_margin_rate=decimal_string(approval_request.candidate_margin_rate),
        request_reason=approval_request.request_reason,
        version=approval_request.version,
        created_at=approval_request.created_at,
        updated_at=approval_request.updated_at,
        decision=decision_response,
    )


def _required_reason(reason: str | None, *, code: str, detail: str) -> str:
    if reason is None or not reason.strip():
        raise ApiError(422, code, detail)
    return reason.strip()


def _selected_candidate_evidence(
    session: Session,
    *,
    quote: Quote,
    payload: ApprovalRequestCreate,
) -> tuple[PricingCheck, PriceCandidate, PriceValidationResult]:
    check = session.scalar(
        select(PricingCheck).where(PricingCheck.id == payload.pricing_check_id).with_for_update()
    )
    if check is None:
        raise ApiError(404, "pricing_check_not_found", "Pricing check was not found")
    if check.quote_id != quote.id:
        raise ApiError(422, "pricing_check_quote_mismatch", "Pricing check does not belong to this quote")
    if quote.version != check.quote_version:
        raise ApiError(409, "stale_pricing_check", "Quote changed after the pricing check")

    source_revision = session.scalar(select(QuoteRevision).where(QuoteRevision.id == check.quote_revision_id))
    if source_revision is None or source_revision.quote_id != quote.id:
        raise ApiError(409, "pricing_check_revision_missing", "Pricing check revision evidence is incomplete")
    if quote.current_revision_number != source_revision.revision_number:
        raise ApiError(409, "stale_pricing_check", "Quote revision changed after the pricing check")

    candidate = session.scalar(
        select(PriceCandidate).where(
            PriceCandidate.id == payload.price_candidate_id,
            PriceCandidate.pricing_check_id == check.id,
        )
    )
    if candidate is None:
        raise ApiError(404, "price_candidate_not_found", "Price candidate was not found for this pricing check")
    if not candidate.is_selected:
        raise ApiError(422, "candidate_not_selected", "Only the selected pricing candidate can be submitted")
    validation = session.scalar(
        select(PriceValidationResult).where(PriceValidationResult.price_candidate_id == candidate.id)
    )
    if validation is None:
        raise ApiError(409, "pricing_validation_missing", "Pricing validation evidence is incomplete")
    return check, candidate, validation


def _revalidate_snapshot(
    session: Session,
    *,
    check: PricingCheck,
    candidate: PriceCandidate,
    persisted_validation: PriceValidationResult,
) -> CandidateValidation:
    """Re-run deterministic validation from immutable server-side snapshot inputs."""

    snapshot = check.cost_snapshot_json
    try:
        material_cost = to_decimal(snapshot["material_cost"])
        labor_cost = to_decimal(snapshot["labor_cost"])
        overhead_cost = to_decimal(snapshot["overhead_cost"])
    except (KeyError, TypeError, ValueError) as error:
        raise ApiError(409, "pricing_evidence_incomplete", "Pricing cost evidence is incomplete") from error

    candidate_lines = list(
        session.scalars(
            select(PriceCandidateLine)
            .where(PriceCandidateLine.price_candidate_id == candidate.id)
            .order_by(PriceCandidateLine.position.asc())
        )
    )
    if not candidate_lines:
        raise ApiError(409, "pricing_evidence_incomplete", "Pricing candidate line evidence is incomplete")
    recalculated = calculate_candidate(
        [
            PricingLineInput(
                quantity=line.quantity,
                material_cost=material_cost,
                labor_cost=labor_cost,
                overhead_cost=overhead_cost,
            )
            for line in candidate_lines
        ],
        margin_rate=candidate.margin_rate,
    )
    if (
        recalculated.total_cost != candidate.total_cost
        or recalculated.total_price != candidate.total_price
        or recalculated.gross_profit != candidate.estimated_gross_profit
        or recalculated.margin_rate != candidate.estimated_margin_rate
    ):
        raise ApiError(409, "pricing_evidence_mismatch", "Pricing candidate does not match its immutable evidence")

    context = check.competitor_context_json
    average_value = context.get("average_unit_price")
    try:
        competitor_average = to_decimal(average_value) if average_value is not None else None
    except (TypeError, ValueError) as error:
        raise ApiError(409, "pricing_evidence_incomplete", "Competitor context evidence is incomplete") from error
    recalculated_validation = validate_candidate(
        recalculated,
        minimum_margin_rate=check.minimum_margin_rate,
        competitor_average_unit_price=competitor_average,
        competitor_context_included=bool(context.get("included")),
    )
    if (
        recalculated_validation.status != persisted_validation.validation_status
        or recalculated_validation.risk_level != persisted_validation.risk_level
        or persisted_validation.minimum_margin_rate != check.minimum_margin_rate
    ):
        raise ApiError(409, "pricing_validation_mismatch", "Pricing validation does not match immutable evidence")

    persisted_checks = list(
        session.scalars(
            select(PriceValidationCheck)
            .where(PriceValidationCheck.price_validation_result_id == persisted_validation.id)
            .order_by(PriceValidationCheck.code.asc())
        )
    )
    expected_checks = sorted(recalculated_validation.checks, key=lambda item: item.code)
    if len(persisted_checks) != len(expected_checks) or any(
        saved.code != expected.code
        or saved.severity != expected.severity
        or saved.passed != expected.passed
        for saved, expected in zip(persisted_checks, expected_checks, strict=True)
    ):
        raise ApiError(409, "pricing_validation_mismatch", "Pricing validation checks do not match immutable evidence")
    return recalculated_validation


def _ensure_submission_eligible(
    *,
    check: PricingCheck,
    validation: CandidateValidation,
    request_reason: str | None,
) -> str | None:
    if (
        check.status == PricingCheckStatus.BLOCKED
        or validation.status == ValidationStatus.FAILED
        or validation.risk_level == RiskLevel.HIGH
    ):
        raise ApiError(409, "blocked_pricing_check", "Failed or high-risk pricing checks cannot be submitted")
    if validation.status == ValidationStatus.WARNING or validation.risk_level == RiskLevel.MEDIUM:
        return _required_reason(
            request_reason,
            code="approval_reason_required",
            detail="A written reason is required for warning or medium-risk pricing",
        )
    if validation.status != ValidationStatus.PASSED or validation.risk_level != RiskLevel.LOW:
        raise ApiError(409, "pricing_check_not_eligible", "Pricing check is not eligible for approval")
    return request_reason.strip() if request_reason else None


def create_approval_request(
    session: Session,
    *,
    payload: ApprovalRequestCreate,
    actor: User,
    request_id: str,
) -> ApprovalRequestResponse:
    quote = QuoteRepository(session).get(payload.quote_id, for_update=True)
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    if quote.status != QuoteStatus.DRAFT:
        raise ApiError(409, "quote_not_submittable", "Only a draft quote can be submitted for approval")
    check, candidate, persisted_validation = _selected_candidate_evidence(session, quote=quote, payload=payload)
    validation = _revalidate_snapshot(
        session,
        check=check,
        candidate=candidate,
        persisted_validation=persisted_validation,
    )
    request_reason = _ensure_submission_eligible(
        check=check,
        validation=validation,
        request_reason=payload.reason,
    )

    approval_request = ApprovalRequest(
        quote_id=quote.id,
        quote_revision_id=check.quote_revision_id,
        quote_version=check.quote_version,
        pricing_check_id=check.id,
        price_candidate_id=candidate.id,
        requester_user_id=actor.id,
        status=ApprovalStatus.PENDING,
        validation_status=validation.status,
        risk_level=validation.risk_level,
        currency=check.currency,
        candidate_total_price=candidate.total_price,
        candidate_gross_profit=candidate.estimated_gross_profit,
        candidate_margin_rate=candidate.estimated_margin_rate,
        request_reason=request_reason,
        version=1,
    )
    session.add(approval_request)
    _flush(session)
    pending_revision = create_workflow_revision(
        session,
        quote=quote,
        target_status=QuoteStatus.APPROVAL_PENDING,
        actor=actor,
    )
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="approval_request.created",
        entity_type="approval_request",
        entity_id=str(approval_request.id),
        request_id=request_id,
        metadata={
            "quote_id": quote.id,
            "quote_revision_id": check.quote_revision_id,
            "pricing_check_id": check.id,
            "price_candidate_id": candidate.id,
            "validation_status": validation.status.value,
            "risk_level": validation.risk_level.value,
            "pending_quote_revision_id": pending_revision.id,
        },
    )
    _commit(session)
    session.refresh(approval_request)
    return _response(session, approval_request)


def get_approval_request(session: Session, approval_request_id: int) -> ApprovalRequestResponse:
    approval_request = session.scalar(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_request_id)
    )
    if approval_request is None:
        raise ApiError(404, "approval_request_not_found", "Approval request was not found")
    return _response(session, approval_request)


def list_approval_requests(
    session: Session,
    *,
    page: int,
    page_size: int,
    status: ApprovalStatus | None,
    quote_id: int | None,
) -> ApprovalRequestPageResponse:
    statement = select(ApprovalRequest)
    count_statement = select(func.count()).select_from(ApprovalRequest)
    filters = []
    if status is not None:
        filters.append(ApprovalRequest.status == status)
    if quote_id is not None:
        filters.append(ApprovalRequest.quote_id == quote_id)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    approval_requests = list(
        session.scalars(
            statement.order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    total = int(session.scalar(count_statement) or 0)
    return ApprovalRequestPageResponse(
        items=[_response(session, approval_request) for approval_request in approval_requests],
        page=page,
        page_size=page_size,
        total=total,
    )


def decide_approval_request(
    session: Session,
    *,
    approval_request_id: int,
    payload: ApprovalDecisionRequest,
    actor: User,
    decision: ApprovalStatus,
    settings: Settings,
    request_id: str,
) -> ApprovalRequestResponse:
    if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
        raise ValueError("Only approval or rejection decisions are supported")
    approval_request = session.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == approval_request_id)
        .with_for_update()
    )
    if approval_request is None:
        raise ApiError(404, "approval_request_not_found", "Approval request was not found")
    if approval_request.status != ApprovalStatus.PENDING:
        raise ApiError(409, "approval_already_decided", "Approval request has already been decided")
    if approval_request.version != payload.version:
        raise ApiError(409, "stale_approval_request", "Approval request changed; refresh before deciding")

    demo_self_approval_used = actor.id == approval_request.requester_user_id
    if demo_self_approval_used and not settings.demo_enabled:
        raise ApiError(403, "self_approval_prohibited", "Requesters cannot review their own approval requests")
    reason = payload.reason.strip() if payload.reason else None
    if decision == ApprovalStatus.REJECTED:
        reason = _required_reason(
            reason,
            code="rejection_reason_required",
            detail="A written reason is required when rejecting an approval request",
        )

    quote = QuoteRepository(session).get(approval_request.quote_id, for_update=True)
    if quote is None:
        raise ApiError(409, "approval_quote_missing", "Approval quote lineage is incomplete")
    if quote.status != QuoteStatus.APPROVAL_PENDING:
        raise ApiError(409, "quote_not_pending_approval", "Quote is not pending approval")

    approval_request.status = decision
    approval_request.version += 1
    _flush(session)
    result_revision = create_workflow_revision(
        session,
        quote=quote,
        target_status=QuoteStatus.APPROVED if decision == ApprovalStatus.APPROVED else QuoteStatus.REJECTED,
        actor=actor,
    )
    approval_decision = ApprovalDecision(
        approval_request_id=approval_request.id,
        decision=decision,
        reviewer_user_id=actor.id,
        reason=reason,
        result_quote_revision_id=result_revision.id,
        demo_self_approval_used=demo_self_approval_used,
    )
    session.add(approval_decision)
    _flush(session)

    reopened_revision_id: int | None = None
    if decision == ApprovalStatus.REJECTED:
        reopened_revision = create_workflow_revision(
            session,
            quote=quote,
            target_status=QuoteStatus.DRAFT,
            actor=actor,
        )
        reopened_revision_id = reopened_revision.id

    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="approval_request.approved" if decision == ApprovalStatus.APPROVED else "approval_request.rejected",
        entity_type="approval_request",
        entity_id=str(approval_request.id),
        request_id=request_id,
        metadata={
            "quote_id": approval_request.quote_id,
            "quote_revision_id": approval_request.quote_revision_id,
            "pricing_check_id": approval_request.pricing_check_id,
            "price_candidate_id": approval_request.price_candidate_id,
            "decision": decision.value,
            "result_quote_revision_id": result_revision.id,
            "reopened_quote_revision_id": reopened_revision_id,
        },
    )
    if demo_self_approval_used:
        append_audit_event(
            session,
            actor_user_id=actor.id,
            action="demo_self_approval_used",
            entity_type="approval_request",
            entity_id=str(approval_request.id),
            request_id=request_id,
            metadata={"decision": decision.value},
        )
    _commit(session)
    session.refresh(approval_request)
    return _response(session, approval_request)
