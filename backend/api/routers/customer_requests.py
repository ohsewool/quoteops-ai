from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, require_minimum_role
from backend.api.errors import ApiError
from backend.domain.customer_requests import CustomerRequestStatus, ProductCode
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.repositories.customer_requests import CustomerRequestRepository
from backend.schemas.customer_requests import (
    CustomerRequestAuditPageResponse,
    CustomerRequestCreate,
    CustomerRequestPageResponse,
    CustomerRequestResponse,
    CustomerRequestTransition,
    CustomerRequestUpdate,
)
from backend.services.customer_requests import (
    create_customer_request,
    customer_request_response,
    get_customer_request,
    request_audit_events,
    transition_customer_request,
    update_customer_request,
)

router = APIRouter(prefix="/api/customer-requests", tags=["customer-requests"])


def _request_id(request: Request) -> str:
    return request.state.request_id


@router.post("", response_model=CustomerRequestResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: CustomerRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CustomerRequestResponse:
    return create_customer_request(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("", response_model=CustomerRequestPageResponse)
def list_customer_requests(
    page: int = 1,
    page_size: int = 25,
    status: CustomerRequestStatus | None = None,
    product_code: ProductCode | None = None,
    assignee_user_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CustomerRequestPageResponse:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(422, "invalid_pagination", "Page must be positive and page size must be between 1 and 100")
    items, total = CustomerRequestRepository(db).list(
        page=page,
        page_size=page_size,
        status=status,
        product_code=product_code,
        assignee_user_id=assignee_user_id,
        search=search.strip() if search else None,
    )
    return CustomerRequestPageResponse(
        items=[customer_request_response(item) for item in items], page=page, page_size=page_size, total=total
    )


@router.get("/{customer_request_id}", response_model=CustomerRequestResponse)
def detail(
    customer_request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CustomerRequestResponse:
    return get_customer_request(db, customer_request_id)


@router.patch("/{customer_request_id}", response_model=CustomerRequestResponse)
def update(
    customer_request_id: int,
    payload: CustomerRequestUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CustomerRequestResponse:
    return update_customer_request(
        db,
        customer_request_id=customer_request_id,
        payload=payload,
        actor=actor,
        request_id=_request_id(request),
    )


@router.post("/{customer_request_id}/transitions", response_model=CustomerRequestResponse)
def transition(
    customer_request_id: int,
    payload: CustomerRequestTransition,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CustomerRequestResponse:
    return transition_customer_request(
        db,
        customer_request_id=customer_request_id,
        payload=payload,
        actor=actor,
        request_id=_request_id(request),
    )


@router.get("/{customer_request_id}/audit-events", response_model=CustomerRequestAuditPageResponse)
def audit_events(
    customer_request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CustomerRequestAuditPageResponse:
    return CustomerRequestAuditPageResponse(items=request_audit_events(db, customer_request_id))
