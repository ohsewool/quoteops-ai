"""Authenticated source-data and deterministic pricing-check HTTP adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, require_minimum_role
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.pricing import (
    CompetitorCreate,
    CompetitorPageResponse,
    CompetitorReferenceCreate,
    CompetitorReferencePageResponse,
    CompetitorReferenceResponse,
    CompetitorResponse,
    CostProfileCreate,
    CostProfilePageResponse,
    CostProfileResponse,
    PricingCheckCreate,
    PricingCheckDetailResponse,
    PricingCheckPageResponse,
    ProductCreate,
    ProductPageResponse,
    ProductResponse,
)
from backend.services.pricing_checks import (
    create_competitor,
    create_competitor_reference,
    create_cost_profile,
    create_pricing_check,
    create_product,
    get_pricing_check,
    list_competitor_references,
    list_competitors,
    list_cost_profiles,
    list_pricing_checks,
    list_products,
)


router = APIRouter(prefix="/api", tags=["pricing-checks"])


def _request_id(request: Request) -> str:
    return request.state.request_id


@router.get("/products", response_model=ProductPageResponse)
def product_list(
    page: int = 1,
    page_size: int = 25,
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProductPageResponse:
    return list_products(db, page=page, page_size=page_size, active=active)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def product_create(
    payload: ProductCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> ProductResponse:
    return create_product(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/cost-profiles", response_model=CostProfilePageResponse)
def cost_profile_list(
    page: int = 1,
    page_size: int = 25,
    product_id: int | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CostProfilePageResponse:
    return list_cost_profiles(db, page=page, page_size=page_size, product_id=product_id, active=active)


@router.post("/cost-profiles", response_model=CostProfileResponse, status_code=status.HTTP_201_CREATED)
def cost_profile_create(
    payload: CostProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CostProfileResponse:
    return create_cost_profile(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/competitors", response_model=CompetitorPageResponse)
def competitor_list(
    page: int = 1,
    page_size: int = 25,
    active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CompetitorPageResponse:
    return list_competitors(db, page=page, page_size=page_size, active=active)


@router.post("/competitors", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
def competitor_create(
    payload: CompetitorCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CompetitorResponse:
    return create_competitor(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/competitor-references", response_model=CompetitorReferencePageResponse)
def competitor_reference_list(
    page: int = 1,
    page_size: int = 25,
    product_id: int | None = None,
    competitor_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CompetitorReferencePageResponse:
    return list_competitor_references(
        db,
        page=page,
        page_size=page_size,
        product_id=product_id,
        competitor_id=competitor_id,
    )


@router.post(
    "/competitor-references",
    response_model=CompetitorReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def competitor_reference_create(
    payload: CompetitorReferenceCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CompetitorReferenceResponse:
    return create_competitor_reference(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.post(
    "/quotes/{quote_id}/pricing-checks",
    response_model=PricingCheckDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def pricing_check_create(
    quote_id: int,
    payload: PricingCheckCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> PricingCheckDetailResponse:
    return create_pricing_check(
        db,
        quote_id=quote_id,
        payload=payload,
        actor=actor,
        request_id=_request_id(request),
    )


@router.get("/quotes/{quote_id}/pricing-checks", response_model=PricingCheckPageResponse)
def pricing_check_list(
    quote_id: int,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PricingCheckPageResponse:
    return list_pricing_checks(db, quote_id=quote_id, page=page, page_size=page_size)


@router.get("/pricing-checks/{pricing_check_id}", response_model=PricingCheckDetailResponse)
def pricing_check_detail(
    pricing_check_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PricingCheckDetailResponse:
    return get_pricing_check(db, pricing_check_id)
