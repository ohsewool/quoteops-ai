from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.domain.customer_requests import CustomerRequestStatus
from backend.domain.money import decimal_string, quantize_money
from backend.domain.quotes import QuoteStatus, quote_is_editable
from backend.models.customer_request import CustomerRequest
from backend.models.quote import Quote, QuoteLine, QuoteRevision, QuoteRevisionLine
from backend.models.user import User
from backend.repositories.quotes import QuoteRepository
from backend.schemas.customer_requests import CustomerRequestTransition
from backend.schemas.quotes import (
    QuoteDetailResponse,
    QuoteDraftUpdate,
    QuoteFromRequestCreate,
    QuoteLineInput,
    QuoteLineResponse,
    QuoteLinesReplace,
    QuoteListItemResponse,
    QuotePageResponse,
    QuoteRevisionDetailResponse,
    QuoteRevisionLineResponse,
    QuoteRevisionPageResponse,
    QuoteRevisionSummaryResponse,
)
from backend.services.audit import append_audit_event
from backend.services.customer_requests import apply_customer_request_transition


def _quote_number() -> str:
    return f"Q-{datetime.now(UTC):%Y%m%d}-{uuid4().hex[:10].upper()}"


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "quote_conflict", "The quote could not be saved") from error


def _flush(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "quote_conflict", "The quote could not be saved") from error


def _require_active_assignee(session: Session, user_id: int | None) -> None:
    if user_id is None:
        return
    user = session.scalar(select(User).where(User.id == user_id, User.active.is_(True)))
    if user is None:
        raise ApiError(422, "invalid_assignee", "The assigned user must be active")


def _quote_list_item(quote: Quote) -> QuoteListItemResponse:
    return QuoteListItemResponse(
        id=quote.id,
        customer_request_id=quote.customer_request_id,
        quote_number=quote.quote_number,
        title=quote.title,
        customer_name=quote.customer_name_snapshot,
        request_product_code=quote.request_product_code,
        request_quantity=quote.request_quantity,
        status=quote.status,
        currency=quote.currency,
        total_amount=decimal_string(quote.total_amount),
        assignee_user_id=quote.assignee_user_id,
        created_by_user_id=quote.created_by_user_id,
        version=quote.version,
        current_revision_number=quote.current_revision_number,
        updated_at=quote.updated_at,
    )


def _line_response(line: QuoteLine) -> QuoteLineResponse:
    return QuoteLineResponse(
        id=line.id,
        position=line.position,
        description=line.description,
        product_code=line.product_code,
        quantity=line.quantity,
        unit_price=decimal_string(line.unit_price),
        line_total=decimal_string(line.line_total),
        options=line.options_json,
    )


def _revision_summary(revision: QuoteRevision) -> QuoteRevisionSummaryResponse:
    return QuoteRevisionSummaryResponse(
        id=revision.id,
        quote_id=revision.quote_id,
        revision_number=revision.revision_number,
        quote_version=revision.quote_version,
        source_request_version=revision.source_request_version,
        status=revision.status,
        total_amount=decimal_string(revision.total_amount),
        currency=revision.currency,
        line_count=revision.line_count,
        formula_version=revision.formula_version,
        rounding_policy_version=revision.rounding_policy_version,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
    )


def _revision_detail(revision: QuoteRevision, lines: list[QuoteRevisionLine]) -> QuoteRevisionDetailResponse:
    return QuoteRevisionDetailResponse(
        **_revision_summary(revision).model_dump(),
        quote_number=revision.quote_number,
        title=revision.title,
        customer_name=revision.customer_name_snapshot,
        contact_name=revision.contact_name_snapshot,
        request_product_code=revision.request_product_code,
        request_quantity=revision.request_quantity,
        notes=revision.notes,
        lines=[
            QuoteRevisionLineResponse(
                id=line.id,
                source_quote_line_id=line.source_quote_line_id,
                position=line.position,
                description=line.description,
                product_code=line.product_code,
                quantity=line.quantity,
                unit_price=decimal_string(line.unit_price),
                line_total=decimal_string(line.line_total),
                options=line.options_json,
            )
            for line in lines
        ],
    )


def _detail_response(session: Session, quote: Quote) -> QuoteDetailResponse:
    repository = QuoteRepository(session)
    revision = repository.revision_for_quote(quote.id, quote.current_revision_number)
    if revision is None:
        raise ApiError(409, "quote_revision_missing", "The quote has no current revision")
    return QuoteDetailResponse(
        **_quote_list_item(quote).model_dump(),
        contact_name=quote.contact_name_snapshot,
        source_request_version=quote.source_request_version,
        formula_version=quote.formula_version,
        rounding_policy_version=quote.rounding_policy_version,
        notes=quote.notes,
        created_at=quote.created_at,
        lines=[_line_response(line) for line in repository.lines_for_quote(quote.id)],
        current_revision=_revision_summary(revision),
    )


def _create_revision_snapshot(
    session: Session,
    *,
    quote: Quote,
    lines: list[QuoteLine],
    actor: User,
) -> QuoteRevision:
    revision = QuoteRevision(
        quote_id=quote.id,
        revision_number=quote.current_revision_number,
        quote_version=quote.version,
        source_request_version=quote.source_request_version,
        status=quote.status,
        quote_number=quote.quote_number,
        title=quote.title,
        customer_name_snapshot=quote.customer_name_snapshot,
        contact_name_snapshot=quote.contact_name_snapshot,
        request_product_code=quote.request_product_code,
        request_quantity=quote.request_quantity,
        currency=quote.currency,
        total_amount=quote.total_amount,
        formula_version=quote.formula_version,
        rounding_policy_version=quote.rounding_policy_version,
        notes=quote.notes,
        line_count=len(lines),
        created_by_user_id=actor.id,
    )
    session.add(revision)
    _flush(session)
    session.add_all(
        [
            QuoteRevisionLine(
                quote_revision_id=revision.id,
                source_quote_line_id=line.id,
                position=line.position,
                description=line.description,
                product_code=line.product_code,
                quantity=line.quantity,
                unit_price=line.unit_price,
                line_total=line.line_total,
                options_json=line.options_json,
            )
            for line in lines
        ]
    )
    _flush(session)
    return revision


def _assert_editable(quote: Quote, version: int) -> None:
    if quote.version != version:
        raise ApiError(409, "stale_quote", "Quote changed; refresh before saving")
    if not quote_is_editable(quote.status):
        raise ApiError(409, "quote_not_editable", "Only draft quotes can be changed")


def _advance_quote(quote: Quote) -> None:
    quote.version += 1
    quote.current_revision_number += 1


def _line_total(unit_price: Decimal, quantity: int) -> Decimal:
    return quantize_money(unit_price * quantity)


def _build_current_lines(session: Session, quote: Quote, payload_lines: list[QuoteLineInput]) -> list[QuoteLine]:
    session.execute(delete(QuoteLine).where(QuoteLine.quote_id == quote.id))
    current_lines = []
    for position, line in enumerate(payload_lines, start=1):
        unit_price = quantize_money(line.unit_price)
        current_lines.append(
            QuoteLine(
                quote_id=quote.id,
                position=position,
                description=line.description,
                product_code=line.product_code,
                quantity=line.quantity,
                unit_price=unit_price,
                line_total=_line_total(unit_price, line.quantity),
                options_json=line.options,
            )
        )
    session.add_all(current_lines)
    _flush(session)
    return current_lines


def create_quote_from_customer_request(
    session: Session,
    *,
    customer_request_id: int,
    payload: QuoteFromRequestCreate,
    actor: User,
    request_id: str,
) -> QuoteDetailResponse:
    customer_request = session.scalar(
        select(CustomerRequest)
        .where(CustomerRequest.id == customer_request_id)
        .with_for_update()
    )
    if customer_request is None:
        raise ApiError(404, "customer_request_not_found", "Customer request was not found")
    if customer_request.version != payload.request_version:
        raise ApiError(409, "stale_customer_request", "Customer request changed; refresh before converting")
    if customer_request.status != CustomerRequestStatus.REVIEWING:
        raise ApiError(409, "request_not_convertible", "Only a reviewing request can become a quote")

    quote = Quote(
        customer_request_id=customer_request.id,
        quote_number=_quote_number(),
        title=payload.title or f"Quote for {customer_request.customer_name}",
        customer_name_snapshot=customer_request.customer_name,
        contact_name_snapshot=customer_request.contact_name,
        request_product_code=customer_request.product_code,
        request_quantity=customer_request.quantity,
        source_request_version=customer_request.version,
        status=QuoteStatus.DRAFT,
        currency="KRW",
        total_amount=Decimal("0.00"),
        formula_version="quote-line-sum-v1",
        rounding_policy_version="krw-half-up-v1",
        notes=payload.notes,
        assignee_user_id=customer_request.assignee_user_id,
        created_by_user_id=actor.id,
        version=1,
        current_revision_number=1,
    )
    session.add(quote)
    _flush(session)
    _create_revision_snapshot(session, quote=quote, lines=[], actor=actor)
    apply_customer_request_transition(
        session,
        customer_request_id=customer_request.id,
        payload=CustomerRequestTransition(version=payload.request_version, target_status=CustomerRequestStatus.QUOTED),
        actor=actor,
        request_id=request_id,
        allow_quote_conversion=True,
    )
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="quote.created",
        entity_type="quote",
        entity_id=str(quote.id),
        request_id=request_id,
        metadata={
            "customer_request_id": customer_request.id,
            "source_request_version": quote.source_request_version,
            "status": quote.status.value,
            "revision_number": quote.current_revision_number,
            "line_count": 0,
            "total_amount": decimal_string(quote.total_amount),
        },
    )
    _commit(session)
    session.refresh(quote)
    return _detail_response(session, quote)


def get_quote(session: Session, quote_id: int) -> QuoteDetailResponse:
    quote = QuoteRepository(session).get(quote_id)
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    return _detail_response(session, quote)


def list_quotes(
    session: Session,
    *,
    page: int,
    page_size: int,
    status: QuoteStatus | None,
    assignee_user_id: int | None,
    customer: str | None,
) -> QuotePageResponse:
    quotes, total = QuoteRepository(session).list(
        page=page,
        page_size=page_size,
        status=status,
        assignee_user_id=assignee_user_id,
        customer=customer,
    )
    return QuotePageResponse(items=[_quote_list_item(quote) for quote in quotes], page=page, page_size=page_size, total=total)


def update_quote_draft(
    session: Session,
    *,
    quote_id: int,
    payload: QuoteDraftUpdate,
    actor: User,
    request_id: str,
) -> QuoteDetailResponse:
    repository = QuoteRepository(session)
    quote = repository.get(quote_id, for_update=True)
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    _assert_editable(quote, payload.version)
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if not changes:
        raise ApiError(422, "no_quote_changes", "At least one quote field must change")
    if "title" in changes and changes["title"] is None:
        raise ApiError(422, "invalid_quote_title", "Quote title cannot be empty")
    if "assignee_user_id" in changes:
        _require_active_assignee(session, changes["assignee_user_id"])
    for field, value in changes.items():
        setattr(quote, field, value)
    _advance_quote(quote)
    lines = repository.lines_for_quote(quote.id)
    _create_revision_snapshot(session, quote=quote, lines=lines, actor=actor)
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="quote.draft_updated",
        entity_type="quote",
        entity_id=str(quote.id),
        request_id=request_id,
        metadata={
            "changed_fields": sorted(changes),
            "previous_version": payload.version,
            "new_version": quote.version,
            "revision_number": quote.current_revision_number,
        },
    )
    _commit(session)
    session.refresh(quote)
    return _detail_response(session, quote)


def replace_quote_lines(
    session: Session,
    *,
    quote_id: int,
    payload: QuoteLinesReplace,
    actor: User,
    request_id: str,
) -> QuoteDetailResponse:
    repository = QuoteRepository(session)
    quote = repository.get(quote_id, for_update=True)
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    _assert_editable(quote, payload.version)
    current_lines = _build_current_lines(session, quote, payload.lines)
    quote.total_amount = quantize_money(sum((line.line_total for line in current_lines), Decimal("0.00")))
    _advance_quote(quote)
    _create_revision_snapshot(session, quote=quote, lines=current_lines, actor=actor)
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="quote.lines_replaced",
        entity_type="quote",
        entity_id=str(quote.id),
        request_id=request_id,
        metadata={
            "previous_version": payload.version,
            "new_version": quote.version,
            "revision_number": quote.current_revision_number,
            "line_count": len(current_lines),
            "total_amount": decimal_string(quote.total_amount),
        },
    )
    _commit(session)
    session.refresh(quote)
    return _detail_response(session, quote)


def list_quote_revisions(session: Session, quote_id: int, *, page: int, page_size: int) -> QuoteRevisionPageResponse:
    repository = QuoteRepository(session)
    if repository.get(quote_id) is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    revisions, total = repository.revisions_for_quote(quote_id, page=page, page_size=page_size)
    return QuoteRevisionPageResponse(
        items=[_revision_summary(revision) for revision in revisions], page=page, page_size=page_size, total=total
    )


def get_quote_revision(session: Session, revision_id: int) -> QuoteRevisionDetailResponse:
    repository = QuoteRepository(session)
    revision = repository.get_revision(revision_id)
    if revision is None:
        raise ApiError(404, "quote_revision_not_found", "Quote revision was not found")
    return _revision_detail(revision, repository.lines_for_revision(revision.id))
