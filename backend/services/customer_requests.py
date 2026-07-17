from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.domain.customer_requests import CustomerRequestStatus, allowed_transitions, is_terminal
from backend.models.audit_event import AuditEvent
from backend.models.customer_request import CustomerRequest
from backend.models.user import User
from backend.repositories.customer_requests import CustomerRequestRepository
from backend.schemas.customer_requests import (
    CustomerRequestAuditEventResponse,
    CustomerRequestCreate,
    CustomerRequestResponse,
    CustomerRequestTransition,
    CustomerRequestUpdate,
)
from backend.services.audit import append_audit_event


def _request_response(request: CustomerRequest) -> CustomerRequestResponse:
    transitions = list(allowed_transitions(request.status))
    # V2-04 owns the atomic request-to-quote conversion. Until then, the API
    # must not advertise a direct quoted transition that it will reject.
    transitions = [
        transition
        for transition in transitions
        if transition != CustomerRequestStatus.QUOTED
    ]
    return CustomerRequestResponse(
        id=request.id,
        customer_name=request.customer_name,
        contact_name=request.contact_name,
        product_code=request.product_code,
        quantity=request.quantity,
        due_date=request.due_date,
        notes=request.notes,
        status=request.status,
        assignee_user_id=request.assignee_user_id,
        created_by_user_id=request.created_by_user_id,
        version=request.version,
        reviewed_at=request.reviewed_at,
        created_at=request.created_at,
        updated_at=request.updated_at,
        ready_for_quote_conversion=request.status == CustomerRequestStatus.REVIEWING,
        allowed_transitions=transitions,
    )


def _active_user_or_error(session: Session, user_id: int | None) -> None:
    if user_id is None:
        return
    user = session.scalar(select(User).where(User.id == user_id, User.active.is_(True)))
    if user is None:
        raise ApiError(422, "invalid_assignee", "The assigned user must be active")


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, "request_conflict", "The request could not be saved") from error


def create_customer_request(
    session: Session,
    *,
    payload: CustomerRequestCreate,
    actor: User,
    request_id: str,
) -> CustomerRequestResponse:
    _active_user_or_error(session, payload.assignee_user_id)
    customer_request = CustomerRequest(
        customer_name=payload.customer_name,
        contact_name=payload.contact_name,
        product_code=payload.product_code,
        quantity=payload.quantity,
        due_date=payload.due_date,
        notes=payload.notes,
        assignee_user_id=payload.assignee_user_id,
        created_by_user_id=actor.id,
        status=CustomerRequestStatus.NEW,
        version=1,
    )
    session.add(customer_request)
    session.flush()
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="customer_request.created",
        entity_type="customer_request",
        entity_id=str(customer_request.id),
        request_id=request_id,
        metadata={"new_status": customer_request.status.value, "product_code": customer_request.product_code.value, "quantity": customer_request.quantity},
    )
    _commit(session)
    session.refresh(customer_request)
    return _request_response(customer_request)


def get_customer_request(session: Session, request_id: int) -> CustomerRequestResponse:
    customer_request = CustomerRequestRepository(session).get(request_id)
    if customer_request is None:
        raise ApiError(404, "customer_request_not_found", "Customer request was not found")
    return _request_response(customer_request)


def update_customer_request(
    session: Session,
    *,
    customer_request_id: int,
    payload: CustomerRequestUpdate,
    actor: User,
    request_id: str,
) -> CustomerRequestResponse:
    repository = CustomerRequestRepository(session)
    customer_request = repository.get(customer_request_id, for_update=True)
    if customer_request is None:
        raise ApiError(404, "customer_request_not_found", "Customer request was not found")
    if customer_request.version != payload.version:
        raise ApiError(409, "stale_customer_request", "Customer request changed; refresh before saving")
    if is_terminal(customer_request.status) or customer_request.status == CustomerRequestStatus.QUOTED:
        raise ApiError(409, "request_not_editable", "This customer request is no longer editable")
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if not changes:
        raise ApiError(422, "no_request_changes", "At least one request field must change")
    if "assignee_user_id" in changes:
        _active_user_or_error(session, changes["assignee_user_id"])
    before = {key: getattr(customer_request, key) for key in changes}
    for key, value in changes.items():
        setattr(customer_request, key, value)
    customer_request.version += 1
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="customer_request.updated",
        entity_type="customer_request",
        entity_id=str(customer_request.id),
        request_id=request_id,
        metadata={"changed_fields": sorted(changes), "previous_version": payload.version, "new_version": customer_request.version, "previous_status": customer_request.status.value, "field_count": len(before)},
    )
    _commit(session)
    session.refresh(customer_request)
    return _request_response(customer_request)


def transition_customer_request(
    session: Session,
    *,
    customer_request_id: int,
    payload: CustomerRequestTransition,
    actor: User,
    request_id: str,
    allow_quote_conversion: bool = False,
) -> CustomerRequestResponse:
    customer_request = apply_customer_request_transition(
        session,
        customer_request_id=customer_request_id,
        payload=payload,
        actor=actor,
        request_id=request_id,
        allow_quote_conversion=allow_quote_conversion,
    )
    _commit(session)
    session.refresh(customer_request)
    return _request_response(customer_request)


def apply_customer_request_transition(
    session: Session,
    *,
    customer_request_id: int,
    payload: CustomerRequestTransition,
    actor: User,
    request_id: str,
    allow_quote_conversion: bool = False,
) -> CustomerRequest:
    """Apply a request transition without committing a surrounding workflow."""

    repository = CustomerRequestRepository(session)
    customer_request = repository.get(customer_request_id, for_update=True)
    if customer_request is None:
        raise ApiError(404, "customer_request_not_found", "Customer request was not found")
    if customer_request.version != payload.version:
        raise ApiError(409, "stale_customer_request", "Customer request changed; refresh before transitioning")
    previous_status = customer_request.status
    if payload.target_status not in allowed_transitions(previous_status):
        raise ApiError(409, "invalid_request_transition", "This customer request transition is not allowed")
    if payload.target_status == CustomerRequestStatus.QUOTED and not allow_quote_conversion:
        raise ApiError(409, "quote_conversion_required", "A persisted quote is required before marking a request quoted")
    customer_request.status = payload.target_status
    customer_request.version += 1
    if payload.target_status == CustomerRequestStatus.REVIEWING and customer_request.reviewed_at is None:
        customer_request.reviewed_at = datetime.now(UTC)
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="customer_request.transitioned",
        entity_type="customer_request",
        entity_id=str(customer_request.id),
        request_id=request_id,
        metadata={"previous_status": previous_status.value, "new_status": customer_request.status.value, "previous_version": payload.version, "new_version": customer_request.version},
    )
    return customer_request


def request_audit_events(session: Session, customer_request_id: int) -> list[CustomerRequestAuditEventResponse]:
    if CustomerRequestRepository(session).get(customer_request_id) is None:
        raise ApiError(404, "customer_request_not_found", "Customer request was not found")
    statement = (
        select(AuditEvent, User.username)
        .join(User, User.id == AuditEvent.actor_user_id)
        .where(AuditEvent.entity_type == "customer_request", AuditEvent.entity_id == str(customer_request_id))
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
    )
    return [
        CustomerRequestAuditEventResponse(
            id=event.id,
            action=event.action,
            actor_user_id=event.actor_user_id,
            actor_username=username,
            request_id=event.request_id,
            metadata=event.metadata_json,
            created_at=event.created_at,
        )
        for event, username in session.execute(statement)
    ]


def customer_request_response(customer_request: CustomerRequest) -> CustomerRequestResponse:
    return _request_response(customer_request)
