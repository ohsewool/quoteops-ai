from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, require_minimum_role
from backend.api.errors import ApiError
from backend.domain.quotes import QuoteStatus
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.quotes import (
    QuoteDetailResponse,
    QuoteDraftUpdate,
    QuoteFromRequestCreate,
    QuoteLinesReplace,
    QuotePageResponse,
    QuoteRevisionDetailResponse,
    QuoteRevisionPageResponse,
)
from backend.services.quotes import (
    create_quote_from_customer_request,
    get_quote,
    get_quote_revision,
    list_quote_revisions,
    list_quotes,
    replace_quote_lines,
    update_quote_draft,
)


router = APIRouter(prefix="/api", tags=["quotes"])


def _request_id(request: Request) -> str:
    return request.state.request_id


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(422, "invalid_pagination", "Page must be positive and page size must be between 1 and 100")


@router.post(
    "/customer-quote-requests/{customer_request_id}/quotes",
    response_model=QuoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def convert_customer_request(
    customer_request_id: int,
    payload: QuoteFromRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> QuoteDetailResponse:
    return create_quote_from_customer_request(
        db,
        customer_request_id=customer_request_id,
        payload=payload,
        actor=actor,
        request_id=_request_id(request),
    )


@router.get("/quotes", response_model=QuotePageResponse)
def quote_list(
    page: int = 1,
    page_size: int = 25,
    status: QuoteStatus | None = None,
    assignee_user_id: int | None = None,
    customer: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> QuotePageResponse:
    _validate_pagination(page, page_size)
    return list_quotes(
        db,
        page=page,
        page_size=page_size,
        status=status,
        assignee_user_id=assignee_user_id,
        customer=customer.strip() if customer else None,
    )


@router.get("/quotes/{quote_id}", response_model=QuoteDetailResponse)
def quote_detail(
    quote_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> QuoteDetailResponse:
    return get_quote(db, quote_id)


@router.patch("/quotes/{quote_id}", response_model=QuoteDetailResponse)
def update_draft(
    quote_id: int,
    payload: QuoteDraftUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> QuoteDetailResponse:
    return update_quote_draft(db, quote_id=quote_id, payload=payload, actor=actor, request_id=_request_id(request))


@router.put("/quotes/{quote_id}/lines", response_model=QuoteDetailResponse)
def replace_lines(
    quote_id: int,
    payload: QuoteLinesReplace,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> QuoteDetailResponse:
    return replace_quote_lines(db, quote_id=quote_id, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/quotes/{quote_id}/revisions", response_model=QuoteRevisionPageResponse)
def revision_list(
    quote_id: int,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> QuoteRevisionPageResponse:
    _validate_pagination(page, page_size)
    return list_quote_revisions(db, quote_id, page=page, page_size=page_size)


@router.get("/quote-revisions/{revision_id}", response_model=QuoteRevisionDetailResponse)
def revision_detail(
    revision_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> QuoteRevisionDetailResponse:
    return get_quote_revision(db, revision_id)
