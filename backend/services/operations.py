"""Restrained operations tools and an isolated, versioned CSV adapter."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.config import Settings
from backend.domain.money import quantize_money
from backend.domain.pricing import ReferencePriceBasis
from backend.models.audit_event import AuditEvent
from backend.models.pricing import Competitor, CompetitorReference, Product
from backend.models.user import User
from backend.schemas.operations import (
    AuditEventPageResponse,
    AuditEventResponse,
    CSV_SCHEMA_VERSION,
    CompetitorReferenceCsvImportResponse,
    OperationsDiagnosticsResponse,
)
from backend.services.audit import append_audit_event, sanitize_metadata


CSV_HEADERS = (
    "product_id",
    "competitor_id",
    "quantity",
    "price_basis",
    "reference_price",
    "observed_at",
    "source_note",
)
MAX_CSV_ROWS = 500
MAX_CSV_FIELD_LENGTH = 10_000
_POSITIVE_INTEGER = re.compile(r"[1-9][0-9]{0,8}$")


@dataclass(frozen=True)
class ParsedCompetitorReference:
    product_id: int
    competitor_id: int
    quantity: int
    price_basis: ReferencePriceBasis
    reference_price: Decimal
    observed_at: datetime
    source_note: str | None


def _pagination_error(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(422, "invalid_pagination", "Pagination values are outside the supported range")


def _csv_error(row: int | None, message: str) -> ApiError:
    field = "csv" if row is None else f"rows.{row}"
    return ApiError(
        422,
        "csv_import_invalid",
        "The competitor-reference CSV could not be imported",
        field_errors=[{"field": field, "message": message}],
    )


def _parse_positive_id(value: str | None, *, row: int, field: str) -> int:
    raw = (value or "").strip()
    if not _POSITIVE_INTEGER.fullmatch(raw):
        raise _csv_error(row, f"{field} must be a positive integer")
    return int(raw)


def _parse_money(value: str | None, *, row: int) -> Decimal:
    raw = (value or "").strip()
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError) as error:
        raise _csv_error(row, "reference_price must be an exact decimal string") from error
    if not parsed.is_finite() or parsed < 0:
        raise _csv_error(row, "reference_price must be a nonnegative finite amount")
    normalized = quantize_money(parsed)
    if normalized != parsed:
        raise _csv_error(row, "reference_price supports at most two decimal places")
    return normalized


def _parse_observed_at(value: str | None, *, row: int) -> datetime:
    raw = (value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise _csv_error(row, "observed_at must be an ISO-8601 timestamp with timezone") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _csv_error(row, "observed_at must include a timezone offset")
    return parsed


def _parse_csv(csv_text: str) -> list[ParsedCompetitorReference]:
    if len(csv_text) > 200_000:
        raise _csv_error(None, "CSV input exceeds the supported size")
    try:
        reader = csv.DictReader(io.StringIO(csv_text, newline=""))
    except csv.Error as error:
        raise _csv_error(None, "CSV parsing failed") from error
    if reader.fieldnames != list(CSV_HEADERS):
        raise _csv_error(None, f"CSV header must exactly match: {','.join(CSV_HEADERS)}")

    parsed_rows: list[ParsedCompetitorReference] = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if len(parsed_rows) >= MAX_CSV_ROWS:
                raise _csv_error(row_number, f"CSV supports at most {MAX_CSV_ROWS} data rows")
            if row is None or None in row:
                raise _csv_error(row_number, "CSV row does not match the required column count")
            if any(value is not None and len(value) > MAX_CSV_FIELD_LENGTH for value in row.values()):
                raise _csv_error(row_number, "CSV field exceeds the supported length")
            try:
                price_basis = ReferencePriceBasis((row.get("price_basis") or "").strip())
            except ValueError as error:
                raise _csv_error(row_number, "price_basis is not supported") from error
            source_note = (row.get("source_note") or "").strip() or None
            if source_note is not None and len(source_note) > 2000:
                raise _csv_error(row_number, "source_note exceeds 2000 characters")
            parsed_rows.append(
                ParsedCompetitorReference(
                    product_id=_parse_positive_id(row.get("product_id"), row=row_number, field="product_id"),
                    competitor_id=_parse_positive_id(row.get("competitor_id"), row=row_number, field="competitor_id"),
                    quantity=_parse_positive_id(row.get("quantity"), row=row_number, field="quantity"),
                    price_basis=price_basis,
                    reference_price=_parse_money(row.get("reference_price"), row=row_number),
                    observed_at=_parse_observed_at(row.get("observed_at"), row=row_number),
                    source_note=source_note,
                )
            )
    except csv.Error as error:
        raise _csv_error(None, "CSV parsing failed") from error
    if not parsed_rows:
        raise _csv_error(None, "CSV must contain at least one data row")
    return parsed_rows


def _audit_response(event: AuditEvent, username: str) -> AuditEventResponse:
    metadata = sanitize_metadata(event.metadata_json)
    return AuditEventResponse(
        id=event.id,
        actor_user_id=event.actor_user_id,
        actor_username=username,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        request_id=event.request_id,
        metadata=metadata if isinstance(metadata, dict) else {},
        created_at=event.created_at,
    )


def list_audit_events(
    session: Session,
    *,
    page: int,
    page_size: int,
    actor: User,
    request_id: str,
    action: str | None = None,
    entity_type: str | None = None,
    actor_user_id: int | None = None,
) -> AuditEventPageResponse:
    _pagination_error(page, page_size)
    conditions = []
    if action:
        conditions.append(AuditEvent.action == action)
    if entity_type:
        conditions.append(AuditEvent.entity_type == entity_type)
    if actor_user_id is not None:
        conditions.append(AuditEvent.actor_user_id == actor_user_id)

    statement = select(AuditEvent, User.username).join(User, User.id == AuditEvent.actor_user_id)
    count_statement = select(func.count(AuditEvent.id))
    if conditions:
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)
    total = int(session.scalar(count_statement) or 0)
    rows = session.execute(
        statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [_audit_response(event, username) for event, username in rows]
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="operations.audit_search_viewed",
        entity_type="audit_event",
        entity_id="search",
        request_id=request_id,
        metadata={
            "has_action_filter": bool(action),
            "has_entity_type_filter": bool(entity_type),
            "has_actor_user_id_filter": actor_user_id is not None,
        },
    )
    session.commit()
    return AuditEventPageResponse(items=items, page=page, page_size=page_size, total=total)


def get_safe_diagnostics(session: Session, *, settings: Settings, actor: User, request_id: str) -> OperationsDiagnosticsResponse:
    try:
        session.execute(text("SELECT 1"))
        revision = session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
        audit_event_count = int(session.scalar(select(func.count(AuditEvent.id))) or 0)
    except SQLAlchemyError as error:
        raise ApiError(503, "operations_unavailable", "Operations diagnostics are unavailable") from error
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="operations.diagnostics_viewed",
        entity_type="system",
        entity_id="diagnostics",
        request_id=request_id,
        metadata={"revision_present": bool(revision)},
    )
    session.commit()
    return OperationsDiagnosticsResponse(
        **settings.safe_summary(),
        database_ready=True,
        alembic_revision=str(revision) if revision else None,
        audit_event_count=audit_event_count,
    )


def import_competitor_references_csv(
    session: Session,
    *,
    csv_text: str,
    actor: User,
    request_id: str,
) -> CompetitorReferenceCsvImportResponse:
    parsed_rows = _parse_csv(csv_text)
    product_ids = sorted({row.product_id for row in parsed_rows})
    competitor_ids = sorted({row.competitor_id for row in parsed_rows})
    products = {product.id for product in session.scalars(select(Product).where(Product.id.in_(product_ids)))}
    competitors = {
        competitor.id: competitor
        for competitor in session.scalars(select(Competitor).where(Competitor.id.in_(competitor_ids)))
    }
    missing_products = sorted(set(product_ids) - products)
    missing_competitors = sorted(set(competitor_ids) - set(competitors))
    inactive_competitors = sorted(
        competitor_id for competitor_id, competitor in competitors.items() if not competitor.active
    )
    if missing_products or missing_competitors or inactive_competitors:
        raise _csv_error(
            None,
            "CSV references missing products, missing competitors, or inactive competitors",
        )

    for row in parsed_rows:
        session.add(
            CompetitorReference(
                competitor_id=row.competitor_id,
                product_id=row.product_id,
                quantity=row.quantity,
                price_basis=row.price_basis,
                reference_price=row.reference_price,
                source_note=row.source_note,
                observed_at=row.observed_at,
                created_by_user_id=actor.id,
            )
        )
    try:
        session.flush()
        append_audit_event(
            session,
            actor_user_id=actor.id,
            action="operations.competitor_reference_csv_imported",
            entity_type="competitor_reference",
            entity_id="csv_import",
            request_id=request_id,
            metadata={
                "schema_version": CSV_SCHEMA_VERSION,
                "imported_count": len(parsed_rows),
                "product_ids": product_ids,
                "competitor_ids": competitor_ids,
            },
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(422, "csv_import_invalid", "The competitor-reference CSV could not be imported") from error
    return CompetitorReferenceCsvImportResponse(
        schema_version=CSV_SCHEMA_VERSION,
        imported_count=len(parsed_rows),
        product_ids=product_ids,
        competitor_ids=competitor_ids,
    )


def export_competitor_references_csv(
    session: Session,
    *,
    actor: User,
    request_id: str,
) -> str:
    rows: Iterable[CompetitorReference] = session.scalars(
        select(CompetitorReference).order_by(CompetitorReference.id.asc())
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(CSV_HEADERS), lineterminator="\n")
    writer.writeheader()
    row_count = 0
    for reference in rows:
        writer.writerow(
            {
                "product_id": reference.product_id,
                "competitor_id": reference.competitor_id,
                "quantity": reference.quantity,
                "price_basis": reference.price_basis.value,
                "reference_price": format(quantize_money(reference.reference_price), "f"),
                "observed_at": reference.observed_at.isoformat(),
                "source_note": reference.source_note or "",
            }
        )
        row_count += 1
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="operations.competitor_reference_csv_exported",
        entity_type="competitor_reference",
        entity_id="csv_export",
        request_id=request_id,
        metadata={"schema_version": CSV_SCHEMA_VERSION, "exported_count": row_count},
    )
    session.commit()
    return output.getvalue()
