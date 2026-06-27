from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    CandidatePriceResponse,
    CustomerQuoteCandidatePriceRequest,
    CustomerQuoteRequestCreate,
    CustomerQuoteRequestResponse,
    CustomerQuoteRequestStatusUpdate,
    CustomerQuoteRequestUpdate,
    QuotePreviewResponse,
)
from backend.services.audit_service import create_audit_log
from backend.services.customer_quote_request_service import (
    candidate_prices_from_request,
    create_customer_quote_request,
    get_customer_quote_request,
    list_customer_quote_requests,
    quote_preview_from_request,
    update_customer_quote_request,
    update_customer_quote_request_status,
)


router = APIRouter(prefix="/api/customer-quote-requests", tags=["customer quote requests"])


@router.post(
    "",
    response_model=CustomerQuoteRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    payload: CustomerQuoteRequestCreate, db: Session = Depends(get_db)
) -> CustomerQuoteRequestResponse:
    response = create_customer_quote_request(db, payload)
    create_audit_log(
        db,
        action="customer_quote_request_created",
        entity_type="customer_quote_request",
        entity_id=response.id,
        summary=f"Customer quote request {response.id} created.",
        metadata={"request_id": response.id, "product_id": response.product_id, "quantity": response.quantity},
    )
    return response


@router.get("", response_model=list[CustomerQuoteRequestResponse])
def list_requests(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> list[CustomerQuoteRequestResponse]:
    return list_customer_quote_requests(db)


@router.get("/{request_id}", response_model=CustomerQuoteRequestResponse)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> CustomerQuoteRequestResponse:
    return get_customer_quote_request(db, request_id)


@router.put("/{request_id}", response_model=CustomerQuoteRequestResponse)
def update_request(
    request_id: int,
    payload: CustomerQuoteRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CustomerQuoteRequestResponse:
    response = update_customer_quote_request(db, request_id, payload)
    create_audit_log(
        db,
        action="customer_quote_request_updated",
        entity_type="customer_quote_request",
        entity_id=response.id,
        summary=f"Customer quote request {response.id} updated.",
        metadata={"request_id": response.id, "status": response.status},
        actor=current_user,
    )
    return response


@router.post("/{request_id}/status", response_model=CustomerQuoteRequestResponse)
def update_request_status(
    request_id: int,
    payload: CustomerQuoteRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CustomerQuoteRequestResponse:
    response = update_customer_quote_request_status(db, request_id, payload)
    create_audit_log(
        db,
        action="customer_quote_request_status_changed",
        entity_type="customer_quote_request",
        entity_id=response.id,
        summary=f"Customer quote request {response.id} status changed to {response.status}.",
        metadata={"request_id": response.id, "status": response.status, "assigned_to_username": response.assigned_to_username},
        actor=current_user,
    )
    return response


@router.post("/{request_id}/quote-preview", response_model=QuotePreviewResponse)
def create_quote_preview_from_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> QuotePreviewResponse:
    response = quote_preview_from_request(db, request_id)
    create_audit_log(
        db,
        action="customer_quote_request_quote_preview_created",
        entity_type="customer_quote_request",
        entity_id=request_id,
        summary=f"Quote preview created from customer quote request {request_id}.",
        metadata={"request_id": request_id, "product_id": response.product_id, "quantity": response.quantity},
        actor=current_user,
    )
    return response


@router.post("/{request_id}/candidate-prices", response_model=CandidatePriceResponse)
def create_candidate_prices_from_request(
    request_id: int,
    payload: CustomerQuoteCandidatePriceRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> CandidatePriceResponse:
    response = candidate_prices_from_request(
        db, request_id, payload or CustomerQuoteCandidatePriceRequest()
    )
    create_audit_log(
        db,
        action="customer_quote_request_candidate_prices_generated",
        entity_type="customer_quote_request",
        entity_id=request_id,
        summary=f"Candidate prices generated from customer quote request {request_id}.",
        metadata={"request_id": request_id, "product_id": response.product_id, "quantity": response.quantity, "candidate_count": len(response.candidates)},
        actor=current_user,
    )
    return response
