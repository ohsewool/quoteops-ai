"""Build immutable, safely rendered report artifacts from approved V2 evidence."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.domain.approvals import ApprovalStatus
from backend.domain.money import decimal_string
from backend.domain.quotes import QuoteStatus
from backend.models.approval import ApprovalDecision, ApprovalRequest
from backend.models.html_report import HtmlReport
from backend.models.pricing import PriceCandidate, PriceCandidateLine, PricingCheck
from backend.models.quote import Quote, QuoteRevision, QuoteRevisionLine
from backend.models.user import User
from backend.schemas.html_reports import (
    HtmlReportCreate,
    HtmlReportHistoryEntry,
    HtmlReportLineResponse,
    HtmlReportResponse,
)
from backend.services.audit import append_audit_event


REPORT_TYPE = "approved_quote"
SNAPSHOT_VERSION = "approved-quote-report-v1"
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "report_conflict", "The report could not be saved") from error


def _flush(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "report_conflict", "The report could not be saved") from error


def _safe_string(value: object | None) -> str:
    return "" if value is None else str(value)


def _approved_source(
    session: Session,
    *,
    approval_request_id: int,
) -> tuple[ApprovalRequest, ApprovalDecision, Quote, QuoteRevision, PricingCheck, PriceCandidate]:
    approval_request = session.scalar(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_request_id)
    )
    if approval_request is None:
        raise ApiError(404, "approval_request_not_found", "Approval request was not found")
    if approval_request.status != ApprovalStatus.APPROVED:
        raise ApiError(409, "report_source_not_approved", "Reports require an approved quote source")

    decision = session.scalar(
        select(ApprovalDecision).where(ApprovalDecision.approval_request_id == approval_request.id)
    )
    if decision is None or decision.decision != ApprovalStatus.APPROVED:
        raise ApiError(409, "report_approval_evidence_incomplete", "Approved decision evidence is incomplete")

    quote = session.scalar(select(Quote).where(Quote.id == approval_request.quote_id))
    source_revision = session.scalar(
        select(QuoteRevision).where(QuoteRevision.id == decision.result_quote_revision_id)
    )
    if (
        quote is None
        or source_revision is None
        or source_revision.quote_id != approval_request.quote_id
        or source_revision.status != QuoteStatus.APPROVED
    ):
        raise ApiError(409, "report_source_revision_incomplete", "Approved quote revision evidence is incomplete")

    pricing_check = session.scalar(select(PricingCheck).where(PricingCheck.id == approval_request.pricing_check_id))
    candidate = session.scalar(select(PriceCandidate).where(PriceCandidate.id == approval_request.price_candidate_id))
    if (
        pricing_check is None
        or candidate is None
        or candidate.pricing_check_id != pricing_check.id
        or pricing_check.quote_id != quote.id
        or pricing_check.quote_revision_id != approval_request.quote_revision_id
    ):
        raise ApiError(409, "report_pricing_evidence_incomplete", "Approved pricing evidence is incomplete")
    if (
        candidate.total_price != approval_request.candidate_total_price
        or candidate.estimated_gross_profit != approval_request.candidate_gross_profit
        or candidate.estimated_margin_rate != approval_request.candidate_margin_rate
    ):
        raise ApiError(409, "report_pricing_evidence_mismatch", "Approved pricing evidence no longer matches its snapshot")
    return approval_request, decision, quote, source_revision, pricing_check, candidate


def _snapshot(
    session: Session,
    *,
    approval_request: ApprovalRequest,
    decision: ApprovalDecision,
    quote: Quote,
    source_revision: QuoteRevision,
    pricing_check: PricingCheck,
    candidate: PriceCandidate,
) -> dict[str, Any]:
    revision_lines = {
        line.id: line
        for line in session.scalars(
            select(QuoteRevisionLine).where(QuoteRevisionLine.quote_revision_id == pricing_check.quote_revision_id)
        )
    }
    candidate_lines = list(
        session.scalars(
            select(PriceCandidateLine)
            .where(PriceCandidateLine.price_candidate_id == candidate.id)
            .order_by(PriceCandidateLine.position.asc())
        )
    )
    if not candidate_lines:
        raise ApiError(409, "report_pricing_evidence_incomplete", "Approved pricing lines are incomplete")

    safe_lines: list[dict[str, object]] = []
    for line in candidate_lines:
        source_line = revision_lines.get(line.source_quote_revision_line_id)
        if source_line is None:
            raise ApiError(409, "report_source_revision_incomplete", "Approved quote line evidence is incomplete")
        safe_lines.append(
            {
                "position": line.position,
                "description": source_line.description,
                "product_code": line.product_code.value,
                "quantity": line.quantity,
                "unit_price": decimal_string(line.unit_price),
                "total_price": decimal_string(line.total_price),
            }
        )

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "quote": {
            "id": quote.id,
            "number": source_revision.quote_number,
            "title": source_revision.title,
            "customer_name": source_revision.customer_name_snapshot,
            "revision_id": source_revision.id,
            "revision_number": source_revision.revision_number,
            "status": source_revision.status.value,
            "currency": source_revision.currency,
            "total_amount": decimal_string(source_revision.total_amount),
            "request_quantity": source_revision.request_quantity,
        },
        "approval": {
            "request_id": approval_request.id,
            "decision_id": decision.id,
            "pricing_check_id": pricing_check.id,
            "price_candidate_id": candidate.id,
            "validation_status": approval_request.validation_status.value,
            "risk_level": approval_request.risk_level.value,
            "candidate_total_cost": decimal_string(candidate.total_cost),
            "candidate_total_price": decimal_string(approval_request.candidate_total_price),
            "candidate_gross_profit": decimal_string(approval_request.candidate_gross_profit),
            "candidate_margin_rate": decimal_string(approval_request.candidate_margin_rate),
            "formula_version": pricing_check.formula_version,
            "validation_rule_version": pricing_check.validation_rule_version,
            "rounding_policy_version": pricing_check.rounding_policy_version,
        },
        "lines": safe_lines,
    }


def _summary(snapshot: dict[str, Any]) -> str:
    quote = snapshot["quote"]
    approval = snapshot["approval"]
    return (
        f"Approved Quote {quote['number']} revision {quote['revision_number']} is grounded in saved "
        f"pricing check {approval['pricing_check_id']} and approval decision {approval['decision_id']}."
    )


def _render_html(*, title: str, snapshot: dict[str, Any], predecessor_report_id: int | None) -> str:
    quote = snapshot["quote"]
    approval = snapshot["approval"]
    line_rows = "".join(
        "<tr>"
        f"<td>{item['position']}</td>"
        f"<td>{escape(_safe_string(item['description']))}</td>"
        f"<td>{escape(_safe_string(item['product_code']))}</td>"
        f"<td>{item['quantity']}</td>"
        f"<td>{escape(_safe_string(item['unit_price']))} KRW</td>"
        f"<td>{escape(_safe_string(item['total_price']))} KRW</td>"
        "</tr>"
        for item in snapshot["lines"]
    )
    predecessor = "Original artifact" if predecessor_report_id is None else f"Regenerated from report #{predecessor_report_id}"
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\">
  <meta http-equiv=\"Content-Security-Policy\" content=\"{CONTENT_SECURITY_POLICY}\">
  <meta name=\"referrer\" content=\"no-referrer\">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; }}
    body {{ color: #17212b; margin: 0; padding: 36px; }}
    main {{ margin: 0 auto; max-width: 860px; }}
    h1 {{ font-size: 26px; margin: 0; }} h2 {{ font-size: 17px; margin-top: 28px; }}
    p, td, th {{ font-size: 14px; line-height: 1.55; }}
    .meta, .notice {{ color: #52616b; }} .notice {{ border-left: 3px solid #05668d; padding-left: 12px; }}
    dl {{ display: grid; grid-template-columns: 180px 1fr; margin: 12px 0; }}
    dt, dd {{ border-top: 1px solid #d6e0e4; margin: 0; padding: 9px 0; }}
    dt {{ color: #52616b; }} table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d6e0e4; padding: 9px 7px; text-align: left; vertical-align: top; }}
  </style>
</head>
<body>
  <main>
    <p class=\"meta\">QuoteOps AI V2 · Approved Quote report</p>
    <h1>{escape(title)}</h1>
    <p class=\"notice\">This read-only artifact is grounded in an approved Quote revision. It does not approve, reject, or activate prices.</p>
    <h2>Source</h2>
    <dl>
      <dt>Quote</dt><dd>{escape(_safe_string(quote['number']))} · revision {quote['revision_number']}</dd>
      <dt>Quote status</dt><dd>{escape(_safe_string(quote['status']))}</dd>
      <dt>Customer</dt><dd>{escape(_safe_string(quote['customer_name']))}</dd>
      <dt>Report lineage</dt><dd>{escape(predecessor)}</dd>
      <dt>Pricing check</dt><dd>#{approval['pricing_check_id']} · candidate #{approval['price_candidate_id']}</dd>
      <dt>Approval decision</dt><dd>#{approval['decision_id']}</dd>
    </dl>
    <h2>Approved pricing summary</h2>
    <dl>
      <dt>Quote total</dt><dd>{escape(_safe_string(quote['total_amount']))} KRW</dd>
      <dt>Candidate total cost</dt><dd>{escape(_safe_string(approval['candidate_total_cost']))} KRW</dd>
      <dt>Candidate total price</dt><dd>{escape(_safe_string(approval['candidate_total_price']))} KRW</dd>
      <dt>Estimated gross profit</dt><dd>{escape(_safe_string(approval['candidate_gross_profit']))} KRW</dd>
      <dt>Estimated margin rate</dt><dd>{escape(_safe_string(approval['candidate_margin_rate']))}</dd>
      <dt>Validation / risk</dt><dd>{escape(_safe_string(approval['validation_status']))} / {escape(_safe_string(approval['risk_level']))}</dd>
    </dl>
    <h2>Approved pricing lines</h2>
    <table>
      <thead><tr><th>#</th><th>Description</th><th>Product</th><th>Quantity</th><th>Unit price</th><th>Total price</th></tr></thead>
      <tbody>{line_rows}</tbody>
    </table>
    <p class=\"notice\">All pricing values are deterministic snapshots. Raw cost components and executable input are intentionally excluded.</p>
  </main>
</body>
</html>"""


def _history(session: Session, report: HtmlReport) -> list[HtmlReportHistoryEntry]:
    reports = list(
        session.scalars(
            select(HtmlReport)
            .where(
                HtmlReport.approval_request_id == report.approval_request_id,
                HtmlReport.source_quote_revision_id == report.source_quote_revision_id,
            )
            .order_by(HtmlReport.created_at.asc(), HtmlReport.id.asc())
        )
    )
    return [
        HtmlReportHistoryEntry(
            id=item.id,
            title=item.title,
            predecessor_report_id=item.predecessor_report_id,
            created_by_user_id=item.created_by_user_id,
            created_at=item.created_at,
        )
        for item in reports
    ]


def _response(session: Session, report: HtmlReport) -> HtmlReportResponse:
    snapshot = report.snapshot_json
    quote = snapshot["quote"]
    approval = snapshot["approval"]
    return HtmlReportResponse(
        id=report.id,
        report_type=report.report_type,
        title=report.title,
        quote_id=report.quote_id,
        source_quote_revision_id=report.source_quote_revision_id,
        source_quote_revision_number=quote["revision_number"],
        source_quote_status=quote["status"],
        source_quote_number=quote["number"],
        approval_request_id=report.approval_request_id,
        approval_decision_id=report.approval_decision_id,
        predecessor_report_id=report.predecessor_report_id,
        created_by_user_id=report.created_by_user_id,
        currency=quote["currency"],
        quote_total_amount=quote["total_amount"],
        candidate_total_cost=approval["candidate_total_cost"],
        candidate_total_price=approval["candidate_total_price"],
        candidate_gross_profit=approval["candidate_gross_profit"],
        candidate_margin_rate=approval["candidate_margin_rate"],
        validation_status=approval["validation_status"],
        risk_level=approval["risk_level"],
        lines=[HtmlReportLineResponse(**item) for item in snapshot["lines"]],
        summary_text=report.summary_text,
        content_sha256=report.content_sha256,
        created_at=report.created_at,
        regeneration_history=_history(session, report),
    )


def _get_report(session: Session, report_id: int) -> HtmlReport:
    report = session.scalar(select(HtmlReport).where(HtmlReport.id == report_id))
    if report is None:
        raise ApiError(404, "html_report_not_found", "HTML report was not found")
    return report


def _validate_predecessor(
    session: Session,
    *,
    predecessor_report_id: int | None,
    approval_request_id: int,
    source_quote_revision_id: int,
    snapshot: dict[str, Any],
) -> HtmlReport | None:
    if predecessor_report_id is None:
        return None
    predecessor = _get_report(session, predecessor_report_id)
    if (
        predecessor.approval_request_id != approval_request_id
        or predecessor.source_quote_revision_id != source_quote_revision_id
        or predecessor.report_type != REPORT_TYPE
    ):
        raise ApiError(422, "report_predecessor_mismatch", "Report predecessor does not share the approved source")
    if predecessor.snapshot_json != snapshot:
        raise ApiError(409, "report_snapshot_mismatch", "Report regeneration source changed unexpectedly")
    return predecessor


def create_html_report(
    session: Session,
    *,
    payload: HtmlReportCreate,
    actor: User,
    request_id: str,
) -> HtmlReportResponse:
    approval_request, decision, quote, source_revision, pricing_check, candidate = _approved_source(
        session,
        approval_request_id=payload.approval_request_id,
    )
    snapshot = _snapshot(
        session,
        approval_request=approval_request,
        decision=decision,
        quote=quote,
        source_revision=source_revision,
        pricing_check=pricing_check,
        candidate=candidate,
    )
    _validate_predecessor(
        session,
        predecessor_report_id=payload.predecessor_report_id,
        approval_request_id=approval_request.id,
        source_quote_revision_id=source_revision.id,
        snapshot=snapshot,
    )
    html_content = _render_html(
        title=payload.title,
        snapshot=snapshot,
        predecessor_report_id=payload.predecessor_report_id,
    )
    report = HtmlReport(
        report_type=REPORT_TYPE,
        title=payload.title,
        quote_id=quote.id,
        source_quote_revision_id=source_revision.id,
        approval_request_id=approval_request.id,
        approval_decision_id=decision.id,
        predecessor_report_id=payload.predecessor_report_id,
        created_by_user_id=actor.id,
        snapshot_json=snapshot,
        summary_text=_summary(snapshot),
        html_content=html_content,
        content_sha256=sha256(html_content.encode("utf-8")).hexdigest(),
    )
    session.add(report)
    _flush(session)
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="html_report.created" if payload.predecessor_report_id is None else "html_report.regenerated",
        entity_type="html_report",
        entity_id=str(report.id),
        request_id=request_id,
        metadata={
            "quote_id": quote.id,
            "source_quote_revision_id": source_revision.id,
            "approval_request_id": approval_request.id,
            "approval_decision_id": decision.id,
            "predecessor_report_id": payload.predecessor_report_id,
            "report_type": REPORT_TYPE,
        },
    )
    _commit(session)
    session.refresh(report)
    return _response(session, report)


def list_html_reports(session: Session) -> list[HtmlReportResponse]:
    reports = list(
        session.scalars(select(HtmlReport).order_by(HtmlReport.created_at.desc(), HtmlReport.id.desc()))
    )
    return [_response(session, report) for report in reports]


def get_html_report(session: Session, report_id: int) -> HtmlReportResponse:
    return _response(session, _get_report(session, report_id))


def get_html_report_content(session: Session, report_id: int) -> HtmlReport:
    return _get_report(session, report_id)


def audit_report_read(
    session: Session,
    *,
    actor: User,
    report_id: int,
    action: str,
    request_id: str,
    metadata: dict[str, object] | None = None,
) -> None:
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action=action,
        entity_type="html_report",
        entity_id=str(report_id),
        request_id=request_id,
        metadata=metadata or {"report_id": report_id},
    )
    _commit(session)
