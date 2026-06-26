from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db import get_connection
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas.quote_request import QuoteRequest, QuoteRequestCreate, QuoteRequestPreviewResponse, QuoteRequestUpdate
from backend.services.quote_calculator import QuoteCalculationError
from backend.services.quote_request_service import (
    QuoteRequestError,
    create_quote_request,
    get_quote_request,
    list_quote_requests,
    preview_quote_for_request,
    update_quote_request,
)
from backend.services.audit_logger import log_audit_event

router = APIRouter(prefix="/api/quote-requests", tags=["quote-requests"])


@router.post("", response_model=QuoteRequest, status_code=201)
def submit_quote_request(request: QuoteRequestCreate) -> dict:
    try:
        with get_connection() as connection:
            result = create_quote_request(connection, request)
            log_audit_event(
                connection,
                action="quote_request_submitted",
                entity_type="quote_request",
                entity_id=result["id"],
                entity_label=result["requester_email"],
                after=result,
            )
            return result
    except QuoteRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("", response_model=list[QuoteRequest])
def read_quote_requests(status: str | None = Query(default=None)) -> list[dict]:
    try:
        with get_connection() as connection:
            return list_quote_requests(connection, status)
    except QuoteRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{request_id}", response_model=QuoteRequest)
def read_quote_request(request_id: int) -> dict:
    try:
        with get_connection() as connection:
            return get_quote_request(connection, request_id)
    except QuoteRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/{request_id}", response_model=QuoteRequest)
def patch_quote_request(
    request_id: int,
    request: QuoteRequestUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            before = get_quote_request(connection, request_id)
            result = update_quote_request(connection, request_id, request)
            log_audit_event(
                connection,
                action="quote_request_updated",
                entity_type="quote_request",
                entity_id=request_id,
                entity_label=result["requester_email"],
                before=before,
                after=result,
            )
            return result
    except QuoteRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{request_id}/preview-quote", response_model=QuoteRequestPreviewResponse)
def preview_quote_request(
    request_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            result = preview_quote_for_request(connection, request_id)
            log_audit_event(
                connection,
                action="quote_request_quoted",
                entity_type="quote_request",
                entity_id=request_id,
                entity_label=result["quote_request"]["requester_email"],
                after={
                    "quote_request": result["quote_request"],
                    "quote_preview": result["quote_preview"],
                },
            )
            return result
    except QuoteRequestError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except QuoteCalculationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
