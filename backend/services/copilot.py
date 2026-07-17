"""Grounded text generation that cannot mutate V2 pricing or workflow state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.domain.approvals import ApprovalStatus
from backend.domain.copilot import CopilotGenerationMode, CopilotPurpose
from backend.domain.money import decimal_string
from backend.domain.quotes import QuoteStatus
from backend.models.approval import ApprovalDecision, ApprovalRequest
from backend.models.copilot_output import CopilotOutput
from backend.models.html_report import HtmlReport
from backend.models.pricing import PriceCandidate, PriceValidationCheck, PriceValidationResult, PricingCheck
from backend.models.quote import Quote, QuoteRevision
from backend.models.user import User
from backend.schemas.copilot import (
    CopilotSourceArtifactResponse,
    CopilotTriggeredRuleResponse,
    GroundedCopilotOutputCreate,
    GroundedCopilotOutputResponse,
)
from backend.services.audit import append_audit_event


SENSITIVE_TEXT_FRAGMENTS = (
    "api_key",
    "authorization",
    "database_url",
    "password",
    "private key",
    "secret",
    "token",
)


class CopilotProviderError(Exception):
    """A sanitized provider outcome that must never block deterministic work."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class CopilotProvider(Protocol):
    name: str
    model: str | None

    def generate(self, *, purpose: CopilotPurpose, grounding: dict[str, object]) -> str:
        ...


class DisabledCopilotProvider:
    name = "disabled"
    model = None

    def generate(self, *, purpose: CopilotPurpose, grounding: dict[str, object]) -> str:
        raise CopilotProviderError("provider_disabled")


@dataclass(frozen=True)
class StaticCopilotProvider:
    """Test-only provider fixture. It makes no network call."""

    text: str
    name: str = "static_fixture"
    model: str | None = "fixture-v1"

    def generate(self, *, purpose: CopilotPurpose, grounding: dict[str, object]) -> str:
        return self.text


@dataclass(frozen=True)
class FailingCopilotProvider:
    code: str = "provider_failure"
    name: str = "failing_fixture"
    model: str | None = "fixture-v1"

    def generate(self, *, purpose: CopilotPurpose, grounding: dict[str, object]) -> str:
        raise CopilotProviderError(self.code)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _flush(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "copilot_output_conflict", "The copilot output could not be saved") from error


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "copilot_output_conflict", "The copilot output could not be saved") from error


def _source_artifact(kind: str, artifact_id: int, created_at: datetime) -> dict[str, object]:
    return {"artifact_type": kind, "artifact_id": artifact_id, "created_at": created_at.isoformat()}


def _require_quote_revision(session: Session, *, quote_id: int, quote_revision_id: int) -> tuple[Quote, QuoteRevision]:
    quote = session.scalar(select(Quote).where(Quote.id == quote_id))
    revision = session.scalar(select(QuoteRevision).where(QuoteRevision.id == quote_revision_id))
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    if revision is None or revision.quote_id != quote.id:
        raise ApiError(422, "copilot_revision_mismatch", "Quote revision does not belong to this quote")
    return quote, revision


def _pricing_source(
    session: Session,
    *,
    quote: Quote,
    revision: QuoteRevision,
    pricing_check_id: int | None,
    price_candidate_id: int | None,
) -> tuple[PricingCheck | None, PriceCandidate | None, PriceValidationResult | None, list[dict[str, object]], list[dict[str, object]], list[datetime]]:
    if pricing_check_id is None and price_candidate_id is None:
        return None, None, None, [], [], []
    if pricing_check_id is None or price_candidate_id is None:
        raise ApiError(422, "copilot_pricing_context_required", "Pricing check and candidate IDs must be supplied together")
    check = session.scalar(select(PricingCheck).where(PricingCheck.id == pricing_check_id))
    candidate = session.scalar(select(PriceCandidate).where(PriceCandidate.id == price_candidate_id))
    if check is None:
        raise ApiError(404, "pricing_check_not_found", "Pricing check was not found")
    if candidate is None:
        raise ApiError(404, "price_candidate_not_found", "Price candidate was not found")
    if check.quote_id != quote.id or check.quote_revision_id != revision.id or candidate.pricing_check_id != check.id:
        raise ApiError(422, "copilot_pricing_context_mismatch", "Pricing evidence does not match this quote revision")
    validation = session.scalar(select(PriceValidationResult).where(PriceValidationResult.price_candidate_id == candidate.id))
    if validation is None:
        raise ApiError(409, "copilot_validation_missing", "Pricing validation evidence is incomplete")
    checks = list(
        session.scalars(
            select(PriceValidationCheck)
            .where(PriceValidationCheck.price_validation_result_id == validation.id)
            .order_by(PriceValidationCheck.code.asc())
        )
    )
    rule_rows = [
        {"code": item.code, "severity": item.severity.value, "passed": item.passed, "message": item.message}
        for item in checks
    ]
    artifacts = [
        _source_artifact("pricing_check", check.id, check.created_at),
        _source_artifact("price_candidate", candidate.id, candidate.created_at),
        _source_artifact("price_validation_result", validation.id, validation.created_at),
    ]
    timestamps = [check.created_at, candidate.created_at, validation.created_at]
    return check, candidate, validation, rule_rows, artifacts, timestamps


def _approval_source(
    session: Session,
    *,
    quote: Quote,
    revision: QuoteRevision,
    approval_request_id: int | None,
) -> tuple[ApprovalRequest | None, ApprovalDecision | None, list[dict[str, object]], list[datetime]]:
    if approval_request_id is None:
        return None, None, [], []
    request = session.scalar(select(ApprovalRequest).where(ApprovalRequest.id == approval_request_id))
    if request is None:
        raise ApiError(404, "approval_request_not_found", "Approval request was not found")
    decision = session.scalar(select(ApprovalDecision).where(ApprovalDecision.approval_request_id == request.id))
    allowed_revision_ids = {request.quote_revision_id}
    if decision is not None:
        allowed_revision_ids.add(decision.result_quote_revision_id)
    if request.quote_id != quote.id or revision.id not in allowed_revision_ids:
        raise ApiError(422, "copilot_approval_context_mismatch", "Approval evidence does not match this quote revision")
    artifacts = [_source_artifact("approval_request", request.id, request.created_at)]
    timestamps = [request.created_at, request.updated_at]
    if decision is not None:
        artifacts.append(_source_artifact("approval_decision", decision.id, decision.created_at))
        timestamps.append(decision.created_at)
    return request, decision, artifacts, timestamps


def _report_source(
    session: Session,
    *,
    quote: Quote,
    revision: QuoteRevision,
    report_id: int | None,
) -> tuple[HtmlReport | None, list[dict[str, object]], list[datetime]]:
    if report_id is None:
        return None, [], []
    report = session.scalar(select(HtmlReport).where(HtmlReport.id == report_id))
    if report is None:
        raise ApiError(404, "html_report_not_found", "HTML report was not found")
    if report.quote_id != quote.id or report.source_quote_revision_id != revision.id:
        raise ApiError(422, "copilot_report_context_mismatch", "Report does not match this quote revision")
    return report, [_source_artifact("html_report", report.id, report.created_at)], [report.created_at]


def _validate_purpose_context(
    *,
    payload: GroundedCopilotOutputCreate,
    pricing_check: PricingCheck | None,
    candidate: PriceCandidate | None,
    validation: PriceValidationResult | None,
    approval_request: ApprovalRequest | None,
    decision: ApprovalDecision | None,
    report: HtmlReport | None,
) -> None:
    if payload.purpose in {CopilotPurpose.CANDIDATE_EXPLANATION, CopilotPurpose.VALIDATION_SUMMARY, CopilotPurpose.APPROVAL_REASON_DRAFT}:
        if pricing_check is None or candidate is None or validation is None:
            raise ApiError(422, "copilot_pricing_context_required", "This copilot purpose requires pricing evidence")
    if payload.purpose == CopilotPurpose.REJECTION_REVISION_SUGGESTION:
        if approval_request is None or decision is None or decision.decision != ApprovalStatus.REJECTED:
            raise ApiError(422, "copilot_rejection_context_required", "This copilot purpose requires a rejected approval decision")
    if payload.purpose == CopilotPurpose.REPORT_SUMMARY_DRAFT and report is None:
        raise ApiError(422, "copilot_report_context_required", "This copilot purpose requires a saved report")


def _grounding(
    *,
    quote: Quote,
    revision: QuoteRevision,
    pricing_check: PricingCheck | None,
    candidate: PriceCandidate | None,
    validation: PriceValidationResult | None,
    approval_request: ApprovalRequest | None,
    decision: ApprovalDecision | None,
    report: HtmlReport | None,
) -> dict[str, object]:
    grounding: dict[str, object] = {
        "quote": {
            "id": quote.id,
            "number": revision.quote_number,
            "revision_id": revision.id,
            "revision_number": revision.revision_number,
            "status": revision.status.value,
            "currency": revision.currency,
            "total_amount": decimal_string(revision.total_amount),
        }
    }
    if pricing_check is not None and candidate is not None and validation is not None:
        grounding["pricing"] = {
            "pricing_check_id": pricing_check.id,
            "price_candidate_id": candidate.id,
            "strategy": candidate.strategy,
            "total_cost": decimal_string(candidate.total_cost),
            "total_price": decimal_string(candidate.total_price),
            "gross_profit": decimal_string(candidate.estimated_gross_profit),
            "margin_rate": decimal_string(candidate.estimated_margin_rate),
            "validation_status": validation.validation_status.value,
            "risk_level": validation.risk_level.value,
            "formula_version": pricing_check.formula_version,
            "validation_rule_version": pricing_check.validation_rule_version,
        }
    if approval_request is not None:
        grounding["approval"] = {
            "approval_request_id": approval_request.id,
            "status": approval_request.status.value,
            "validation_status": approval_request.validation_status.value,
            "risk_level": approval_request.risk_level.value,
            "decision_id": decision.id if decision is not None else None,
            "decision": decision.decision.value if decision is not None else None,
        }
    if report is not None:
        grounding["report"] = {
            "report_id": report.id,
            "content_sha256": report.content_sha256,
            "predecessor_report_id": report.predecessor_report_id,
        }
    return grounding


def _fallback_text(purpose: CopilotPurpose, grounding: dict[str, object], rules: list[dict[str, object]]) -> str:
    quote = grounding["quote"]
    pricing = grounding.get("pricing")
    approval = grounding.get("approval")
    report = grounding.get("report")
    if purpose == CopilotPurpose.CANDIDATE_EXPLANATION:
        assert isinstance(pricing, dict)
        return (
            f"저장된 후보 #{pricing['price_candidate_id']}는 {pricing['strategy']} 전략으로 계산되었습니다. "
            f"총 가격은 {pricing['total_price']} KRW, 예상 마진은 {pricing['margin_rate']}이며 "
            f"검증 상태는 {pricing['validation_status']} / 위험도는 {pricing['risk_level']}입니다."
        )
    if purpose == CopilotPurpose.VALIDATION_SUMMARY:
        assert isinstance(pricing, dict)
        rule_summary = "; ".join(
            f"{item['code']}: {'통과' if item['passed'] else '검토 필요'}" for item in rules
        ) or "저장된 검증 규칙이 없습니다"
        return (
            f"가격 점검 #{pricing['pricing_check_id']}의 저장된 검증 결과는 "
            f"{pricing['validation_status']} / {pricing['risk_level']}입니다. {rule_summary}."
        )
    if purpose == CopilotPurpose.APPROVAL_REASON_DRAFT:
        assert isinstance(pricing, dict)
        return (
            f"저장된 가격 점검 #{pricing['pricing_check_id']}의 {pricing['validation_status']} 결과와 "
            f"{pricing['risk_level']} 위험도를 검토했습니다. 고객 가격 적용 전 별도 담당자의 근거 확인이 필요합니다."
        )
    if purpose == CopilotPurpose.REJECTION_REVISION_SUGGESTION:
        assert isinstance(approval, dict)
        return (
            f"반려된 승인 요청 #{approval['approval_request_id']}의 immutable 근거는 유지합니다. "
            f"새 draft revision에서 저장된 validation/risk 근거를 다시 검토하고, 변경이 필요하면 새 pricing check와 새 승인 요청을 만드세요."
        )
    assert purpose == CopilotPurpose.REPORT_SUMMARY_DRAFT
    assert isinstance(report, dict)
    return (
        f"리포트 #{report['report_id']}는 Quote {quote['number']} revision {quote['revision_number']}의 "
        "승인된 저장 근거를 요약합니다. 이 초안은 가격, 검증, 승인 또는 리포트 상태를 변경하지 않습니다."
    )


def _guard_provider_text(value: str) -> str:
    text = value.strip()
    if not text or len(text) > 4000:
        raise CopilotProviderError("provider_output_invalid")
    lowered = text.lower()
    if "<" in text or ">" in text or any(fragment in lowered for fragment in SENSITIVE_TEXT_FRAGMENTS):
        raise CopilotProviderError("provider_output_unsupported")
    return text


def _generate_text(
    *,
    provider: CopilotProvider,
    purpose: CopilotPurpose,
    grounding: dict[str, object],
    fallback: str,
) -> tuple[str, bool, CopilotGenerationMode, str, str | None, dict[str, object]]:
    try:
        output = _guard_provider_text(provider.generate(purpose=purpose, grounding=grounding))
    except CopilotProviderError as error:
        return (
            fallback,
            True,
            CopilotGenerationMode.FALLBACK,
            provider.name,
            provider.model,
            {"provider_status": "fallback", "reason": error.code},
        )
    return (
        output,
        False,
        CopilotGenerationMode.PROVIDER,
        provider.name,
        provider.model,
        {"provider_status": "generated"},
    )


def _response(output: CopilotOutput) -> GroundedCopilotOutputResponse:
    return GroundedCopilotOutputResponse(
        id=output.id,
        purpose=output.purpose,
        quote_id=output.quote_id,
        quote_revision_id=output.quote_revision_id,
        pricing_check_id=output.pricing_check_id,
        price_candidate_id=output.price_candidate_id,
        approval_request_id=output.approval_request_id,
        report_id=output.report_id,
        created_by_user_id=output.created_by_user_id,
        generated_text=output.generated_text,
        grounding=output.grounding_json,
        source_artifacts=[CopilotSourceArtifactResponse(**item) for item in output.source_artifacts_json],
        triggered_rules=[CopilotTriggeredRuleResponse(**item) for item in output.triggered_rules_json],
        source_data_timestamp=output.source_data_timestamp,
        deterministic_fallback=output.deterministic_fallback,
        generation_mode=output.generation_mode,
        provider_name=output.provider_name,
        provider_model=output.provider_model,
        provider_metadata=output.provider_metadata_json,
        generated_at=output.generated_at,
        created_at=output.created_at,
    )


def create_grounded_copilot_output(
    session: Session,
    *,
    quote_id: int,
    payload: GroundedCopilotOutputCreate,
    actor: User,
    request_id: str,
    provider: CopilotProvider | None = None,
) -> GroundedCopilotOutputResponse:
    quote, revision = _require_quote_revision(session, quote_id=quote_id, quote_revision_id=payload.quote_revision_id)
    pricing_check, candidate, validation, rules, pricing_artifacts, pricing_timestamps = _pricing_source(
        session,
        quote=quote,
        revision=revision,
        pricing_check_id=payload.pricing_check_id,
        price_candidate_id=payload.price_candidate_id,
    )
    approval_request, decision, approval_artifacts, approval_timestamps = _approval_source(
        session,
        quote=quote,
        revision=revision,
        approval_request_id=payload.approval_request_id,
    )
    report, report_artifacts, report_timestamps = _report_source(
        session,
        quote=quote,
        revision=revision,
        report_id=payload.report_id,
    )
    _validate_purpose_context(
        payload=payload,
        pricing_check=pricing_check,
        candidate=candidate,
        validation=validation,
        approval_request=approval_request,
        decision=decision,
        report=report,
    )
    grounding = _grounding(
        quote=quote,
        revision=revision,
        pricing_check=pricing_check,
        candidate=candidate,
        validation=validation,
        approval_request=approval_request,
        decision=decision,
        report=report,
    )
    artifacts = [_source_artifact("quote_revision", revision.id, revision.created_at), *pricing_artifacts, *approval_artifacts, *report_artifacts]
    timestamps = [revision.created_at, *pricing_timestamps, *approval_timestamps, *report_timestamps]
    source_data_timestamp = max(timestamps)
    fallback = _fallback_text(payload.purpose, grounding, rules)
    generated_at = _utcnow()
    text, deterministic_fallback, generation_mode, provider_name, provider_model, provider_metadata = _generate_text(
        provider=provider or DisabledCopilotProvider(),
        purpose=payload.purpose,
        grounding=grounding,
        fallback=fallback,
    )
    output = CopilotOutput(
        purpose=payload.purpose.value,
        quote_id=quote.id,
        quote_revision_id=revision.id,
        pricing_check_id=pricing_check.id if pricing_check is not None else None,
        price_candidate_id=candidate.id if candidate is not None else None,
        approval_request_id=approval_request.id if approval_request is not None else None,
        report_id=report.id if report is not None else None,
        created_by_user_id=actor.id,
        generated_text=text,
        grounding_json=grounding,
        source_artifacts_json=artifacts,
        triggered_rules_json=rules,
        deterministic_fallback=deterministic_fallback,
        generation_mode=generation_mode.value,
        provider_name=provider_name,
        provider_model=provider_model,
        provider_metadata_json=provider_metadata,
        source_data_timestamp=source_data_timestamp,
        generated_at=generated_at,
    )
    session.add(output)
    _flush(session)
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="copilot_output.created",
        entity_type="copilot_output",
        entity_id=str(output.id),
        request_id=request_id,
        metadata={
            "purpose": output.purpose,
            "quote_id": quote.id,
            "quote_revision_id": revision.id,
            "pricing_check_id": output.pricing_check_id,
            "price_candidate_id": output.price_candidate_id,
            "approval_request_id": output.approval_request_id,
            "report_id": output.report_id,
            "deterministic_fallback": output.deterministic_fallback,
            "generation_mode": output.generation_mode,
            "provider_name": output.provider_name,
        },
    )
    _commit(session)
    session.refresh(output)
    return _response(output)


def get_grounded_copilot_output(session: Session, output_id: int) -> GroundedCopilotOutputResponse:
    output = session.scalar(select(CopilotOutput).where(CopilotOutput.id == output_id))
    if output is None:
        raise ApiError(404, "copilot_output_not_found", "Copilot output was not found")
    return _response(output)
