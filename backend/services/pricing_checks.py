"""Persistent deterministic pricing-check orchestration for V2-05."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.domain.customer_requests import ProductCode
from backend.domain.money import decimal_string, quantize_rate
from backend.domain.pricing import (
    CANDIDATE_FORMULA_VERSION,
    COMPETITOR_CONTEXT_VERSION,
    DEFAULT_MARGIN_RATES,
    DEFAULT_STRATEGIES,
    PRICING_ROUNDING_POLICY_VERSION,
    VALIDATION_RULE_VERSION,
    PricingCheckStatus,
    PricingStrategy,
    ReferencePriceBasis,
)
from backend.models.pricing import (
    Competitor,
    CompetitorReference,
    CostProfile,
    PriceCandidate,
    PriceCandidateLine,
    PriceValidationCheck,
    PriceValidationResult,
    PricingCheck,
    Product,
)
from backend.models.quote import Quote, QuoteRevision, QuoteRevisionLine
from backend.models.user import User
from backend.schemas.pricing import (
    CompetitorContextSummaryResponse,
    CompetitorCreate,
    CompetitorPageResponse,
    CompetitorReferenceCreate,
    CompetitorReferencePageResponse,
    CompetitorReferenceResponse,
    CompetitorResponse,
    CostProfileCreate,
    CostProfilePageResponse,
    CostProfileResponse,
    PriceCandidateLineResponse,
    PriceCandidateResponse,
    PricingCheckCreate,
    PricingCheckDetailResponse,
    PricingCheckPageResponse,
    PricingCheckSummaryResponse,
    PricingValidationCheckResponse,
    PricingValidationResponse,
    ProductCreate,
    ProductPageResponse,
    ProductResponse,
)
from backend.services.audit import append_audit_event
from backend.services.pricing_engine import PricingLineInput, calculate_candidate, validate_candidate


def _commit(session: Session, *, code: str, detail: str) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, code, detail) from error


def _flush(session: Session, *, code: str, detail: str) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, code, detail) from error


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApiError(422, "invalid_pagination", "Page must be positive and page size must be between 1 and 100")


def _product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        code=product.code,
        name=product.name,
        description=product.description,
        active=product.active,
        version=product.version,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _cost_profile_response(profile: CostProfile) -> CostProfileResponse:
    return CostProfileResponse(
        id=profile.id,
        product_id=profile.product_id,
        material_cost=decimal_string(profile.material_cost),
        labor_cost=decimal_string(profile.labor_cost),
        overhead_cost=decimal_string(profile.overhead_cost),
        target_margin_rate=decimal_string(profile.target_margin_rate, rate=True),
        active=profile.active,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _competitor_response(competitor: Competitor) -> CompetitorResponse:
    return CompetitorResponse(
        id=competitor.id,
        name=competitor.name,
        competitor_type=competitor.competitor_type,
        notes=competitor.notes,
        active=competitor.active,
        version=competitor.version,
        created_at=competitor.created_at,
        updated_at=competitor.updated_at,
    )


def _reference_response(reference: CompetitorReference) -> CompetitorReferenceResponse:
    return CompetitorReferenceResponse(
        id=reference.id,
        competitor_id=reference.competitor_id,
        product_id=reference.product_id,
        quantity=reference.quantity,
        price_basis=reference.price_basis,
        reference_price=decimal_string(reference.reference_price),
        source_note=reference.source_note,
        observed_at=reference.observed_at,
        created_at=reference.created_at,
    )


def create_product(
    session: Session, *, payload: ProductCreate, actor: User, request_id: str
) -> ProductResponse:
    product = Product(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        active=payload.active,
        created_by_user_id=actor.id,
    )
    session.add(product)
    _flush(session, code="product_conflict", detail="A product with this code already exists")
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="product.created",
        entity_type="product",
        entity_id=str(product.id),
        request_id=request_id,
        metadata={"product_code": product.code.value, "active": product.active},
    )
    _commit(session, code="product_conflict", detail="The product could not be saved")
    session.refresh(product)
    return _product_response(product)


def list_products(session: Session, *, page: int, page_size: int, active: bool | None) -> ProductPageResponse:
    _validate_pagination(page, page_size)
    statement = select(Product)
    count_statement = select(func.count()).select_from(Product)
    if active is not None:
        statement = statement.where(Product.active.is_(active))
        count_statement = count_statement.where(Product.active.is_(active))
    items = list(
        session.scalars(statement.order_by(Product.code.asc()).offset((page - 1) * page_size).limit(page_size))
    )
    total = int(session.scalar(count_statement) or 0)
    return ProductPageResponse(items=[_product_response(product) for product in items], page=page, page_size=page_size, total=total)


def create_cost_profile(
    session: Session, *, payload: CostProfileCreate, actor: User, request_id: str
) -> CostProfileResponse:
    product = session.scalar(select(Product).where(Product.id == payload.product_id).with_for_update())
    if product is None:
        raise ApiError(404, "product_not_found", "Product was not found")
    if not product.active:
        raise ApiError(409, "inactive_product", "A cost profile cannot be created for an inactive product")
    if payload.active:
        existing = session.scalar(
            select(CostProfile)
            .where(CostProfile.product_id == product.id, CostProfile.active.is_(True))
            .with_for_update()
        )
        if existing is not None:
            existing.active = False
            existing.version += 1
    profile = CostProfile(
        product_id=product.id,
        material_cost=payload.material_cost,
        labor_cost=payload.labor_cost,
        overhead_cost=payload.overhead_cost,
        target_margin_rate=quantize_rate(payload.target_margin_rate),
        active=payload.active,
        created_by_user_id=actor.id,
    )
    session.add(profile)
    _flush(session, code="cost_profile_conflict", detail="The cost profile could not be saved")
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="cost_profile.created",
        entity_type="cost_profile",
        entity_id=str(profile.id),
        request_id=request_id,
        metadata={"product_id": profile.product_id, "active": profile.active, "version": profile.version},
    )
    _commit(session, code="cost_profile_conflict", detail="The cost profile could not be saved")
    session.refresh(profile)
    return _cost_profile_response(profile)


def list_cost_profiles(
    session: Session, *, page: int, page_size: int, product_id: int | None, active: bool | None
) -> CostProfilePageResponse:
    _validate_pagination(page, page_size)
    statement = select(CostProfile)
    count_statement = select(func.count()).select_from(CostProfile)
    filters = []
    if product_id is not None:
        filters.append(CostProfile.product_id == product_id)
    if active is not None:
        filters.append(CostProfile.active.is_(active))
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    items = list(
        session.scalars(
            statement.order_by(CostProfile.created_at.desc(), CostProfile.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    total = int(session.scalar(count_statement) or 0)
    return CostProfilePageResponse(
        items=[_cost_profile_response(profile) for profile in items], page=page, page_size=page_size, total=total
    )


def create_competitor(
    session: Session, *, payload: CompetitorCreate, actor: User, request_id: str
) -> CompetitorResponse:
    competitor = Competitor(
        name=payload.name,
        competitor_type=payload.competitor_type,
        notes=payload.notes,
        active=payload.active,
        created_by_user_id=actor.id,
    )
    session.add(competitor)
    _flush(session, code="competitor_conflict", detail="The competitor could not be saved")
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="competitor.created",
        entity_type="competitor",
        entity_id=str(competitor.id),
        request_id=request_id,
        metadata={"competitor_type": competitor.competitor_type.value, "active": competitor.active},
    )
    _commit(session, code="competitor_conflict", detail="The competitor could not be saved")
    session.refresh(competitor)
    return _competitor_response(competitor)


def list_competitors(session: Session, *, page: int, page_size: int, active: bool | None) -> CompetitorPageResponse:
    _validate_pagination(page, page_size)
    statement = select(Competitor)
    count_statement = select(func.count()).select_from(Competitor)
    if active is not None:
        statement = statement.where(Competitor.active.is_(active))
        count_statement = count_statement.where(Competitor.active.is_(active))
    items = list(
        session.scalars(
            statement.order_by(Competitor.name.asc(), Competitor.id.asc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    total = int(session.scalar(count_statement) or 0)
    return CompetitorPageResponse(
        items=[_competitor_response(competitor) for competitor in items], page=page, page_size=page_size, total=total
    )


def create_competitor_reference(
    session: Session, *, payload: CompetitorReferenceCreate, actor: User, request_id: str
) -> CompetitorReferenceResponse:
    competitor = session.scalar(select(Competitor).where(Competitor.id == payload.competitor_id))
    if competitor is None:
        raise ApiError(404, "competitor_not_found", "Competitor was not found")
    if not competitor.active:
        raise ApiError(409, "inactive_competitor", "A reference cannot be created for an inactive competitor")
    product = session.scalar(select(Product).where(Product.id == payload.product_id))
    if product is None:
        raise ApiError(404, "product_not_found", "Product was not found")
    reference = CompetitorReference(
        competitor_id=competitor.id,
        product_id=product.id,
        quantity=payload.quantity,
        price_basis=payload.price_basis,
        reference_price=payload.reference_price,
        source_note=payload.source_note,
        observed_at=payload.observed_at,
        created_by_user_id=actor.id,
    )
    session.add(reference)
    _flush(session, code="competitor_reference_conflict", detail="The competitor reference could not be saved")
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="competitor_reference.created",
        entity_type="competitor_reference",
        entity_id=str(reference.id),
        request_id=request_id,
        metadata={
            "competitor_id": reference.competitor_id,
            "product_id": reference.product_id,
            "quantity": reference.quantity,
            "price_basis": reference.price_basis.value,
        },
    )
    _commit(session, code="competitor_reference_conflict", detail="The competitor reference could not be saved")
    session.refresh(reference)
    return _reference_response(reference)


def list_competitor_references(
    session: Session, *, page: int, page_size: int, product_id: int | None, competitor_id: int | None
) -> CompetitorReferencePageResponse:
    _validate_pagination(page, page_size)
    statement = select(CompetitorReference)
    count_statement = select(func.count()).select_from(CompetitorReference)
    filters = []
    if product_id is not None:
        filters.append(CompetitorReference.product_id == product_id)
    if competitor_id is not None:
        filters.append(CompetitorReference.competitor_id == competitor_id)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)
    items = list(
        session.scalars(
            statement.order_by(CompetitorReference.observed_at.desc(), CompetitorReference.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    total = int(session.scalar(count_statement) or 0)
    return CompetitorReferencePageResponse(
        items=[_reference_response(reference) for reference in items], page=page, page_size=page_size, total=total
    )


def _pricing_check_status(validation_status) -> PricingCheckStatus:
    if validation_status.value == "failed":
        return PricingCheckStatus.BLOCKED
    if validation_status.value == "warning":
        return PricingCheckStatus.NEEDS_REVIEW
    return PricingCheckStatus.READY


def _assert_current_quote_revision(
    session: Session, *, quote_id: int, payload: PricingCheckCreate
) -> tuple[Quote, QuoteRevision, list[QuoteRevisionLine]]:
    quote = session.scalar(select(Quote).where(Quote.id == quote_id).with_for_update())
    if quote is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    if quote.version != payload.quote_version:
        raise ApiError(409, "stale_quote", "The quote version is no longer current")
    revision = session.scalar(select(QuoteRevision).where(QuoteRevision.id == payload.quote_revision_id))
    if revision is None or revision.quote_id != quote.id:
        raise ApiError(422, "invalid_quote_revision", "The quote revision does not belong to this quote")
    if revision.revision_number != quote.current_revision_number or revision.quote_version != quote.version:
        raise ApiError(409, "stale_quote_revision", "Pricing checks must use the current immutable quote revision")
    lines = list(
        session.scalars(
            select(QuoteRevisionLine)
            .where(QuoteRevisionLine.quote_revision_id == revision.id)
            .order_by(QuoteRevisionLine.position.asc())
        )
    )
    if not lines:
        raise ApiError(422, "quote_has_no_lines", "A pricing check requires at least one quote line")
    if any(line.product_code != quote.request_product_code for line in lines):
        raise ApiError(
            422,
            "mixed_quote_products_not_supported",
            "A V2 pricing check requires all quote lines to use the request product",
        )
    return quote, revision, lines


def _source_context(
    session: Session,
    *,
    product_code: ProductCode,
    line_quantities: set[int],
    include_competitor_context: bool,
) -> tuple[Product, CostProfile, dict[str, object], Decimal | None]:
    product = session.scalar(select(Product).where(Product.code == product_code, Product.active.is_(True)))
    if product is None:
        raise ApiError(409, "active_product_not_found", "The quote product is not configured as an active V2 product")
    cost_profile = session.scalar(
        select(CostProfile).where(CostProfile.product_id == product.id, CostProfile.active.is_(True)).with_for_update()
    )
    if cost_profile is None:
        raise ApiError(409, "active_cost_profile_not_found", "An active cost profile is required for this pricing check")

    references: list[CompetitorReference] = []
    normalized_prices: list[Decimal] = []
    if include_competitor_context:
        references = list(
            session.scalars(
                select(CompetitorReference)
                .join(Competitor, Competitor.id == CompetitorReference.competitor_id)
                .where(
                    CompetitorReference.product_id == product.id,
                    CompetitorReference.quantity.in_(line_quantities),
                    Competitor.active.is_(True),
                )
                .order_by(CompetitorReference.observed_at.asc(), CompetitorReference.id.asc())
            )
        )
        normalized_prices = [
            reference.reference_price
            if reference.price_basis is ReferencePriceBasis.UNIT_PRICE
            else reference.reference_price / reference.quantity
            for reference in references
        ]
    average = sum(normalized_prices, Decimal("0")) / len(normalized_prices) if normalized_prices else None
    context = {
        "source_version": COMPETITOR_CONTEXT_VERSION,
        "included": include_competitor_context,
        "reference_ids": [reference.id for reference in references],
        "reference_count": len(references),
        "average_unit_price": decimal_string(average) if average is not None else None,
        "earliest_observed_at": references[0].observed_at.isoformat() if references else None,
        "latest_observed_at": references[-1].observed_at.isoformat() if references else None,
        "reference_snapshot": [
            {
                "reference_id": reference.id,
                "competitor_id": reference.competitor_id,
                "quantity": reference.quantity,
                "price_basis": reference.price_basis.value,
                "reference_price": decimal_string(reference.reference_price),
                "normalized_unit_price": decimal_string(normalized_price),
                "observed_at": reference.observed_at.isoformat(),
            }
            for reference, normalized_price in zip(references, normalized_prices, strict=True)
        ],
    }
    return product, cost_profile, context, average


def create_pricing_check(
    session: Session,
    *,
    quote_id: int,
    payload: PricingCheckCreate,
    actor: User,
    request_id: str,
) -> PricingCheckDetailResponse:
    quote, revision, revision_lines = _assert_current_quote_revision(session, quote_id=quote_id, payload=payload)
    product, cost_profile, competitor_context, competitor_average = _source_context(
        session,
        product_code=quote.request_product_code,
        line_quantities={line.quantity for line in revision_lines},
        include_competitor_context=payload.include_competitor_context,
    )
    source_lines = [
        PricingLineInput(
            quantity=line.quantity,
            material_cost=cost_profile.material_cost,
            labor_cost=cost_profile.labor_cost,
            overhead_cost=cost_profile.overhead_cost,
        )
        for line in revision_lines
    ]
    candidates: list[tuple[PricingStrategy, Decimal, object, object]] = []
    for strategy, margin_rate in zip(DEFAULT_STRATEGIES, DEFAULT_MARGIN_RATES, strict=True):
        calculated = calculate_candidate(source_lines, margin_rate=margin_rate)
        validation = validate_candidate(
            calculated,
            minimum_margin_rate=cost_profile.target_margin_rate,
            competitor_average_unit_price=competitor_average,
            competitor_context_included=payload.include_competitor_context,
        )
        candidates.append((strategy, margin_rate, calculated, validation))
    selected = next((candidate for candidate in candidates if candidate[0] == payload.selected_strategy), None)
    if selected is None:
        raise ApiError(422, "invalid_pricing_strategy", "The selected pricing strategy is not supported")
    selected_strategy, _, selected_calculated, selected_validation = selected
    check = PricingCheck(
        quote_id=quote.id,
        quote_revision_id=revision.id,
        quote_version=quote.version,
        status=_pricing_check_status(selected_validation.status),
        selected_strategy=selected_strategy.value,
        currency="KRW",
        total_cost=selected_calculated.total_cost,
        selected_total_price=selected_calculated.total_price,
        selected_gross_profit=selected_calculated.gross_profit,
        selected_margin_rate=selected_calculated.margin_rate,
        minimum_margin_rate=quantize_rate(cost_profile.target_margin_rate),
        formula_version=CANDIDATE_FORMULA_VERSION,
        validation_rule_version=VALIDATION_RULE_VERSION,
        rounding_policy_version=PRICING_ROUNDING_POLICY_VERSION,
        cost_snapshot_json={
            "product_id": product.id,
            "product_code": product.code.value,
            "cost_profile_id": cost_profile.id,
            "cost_profile_version": cost_profile.version,
            "material_cost": decimal_string(cost_profile.material_cost),
            "labor_cost": decimal_string(cost_profile.labor_cost),
            "overhead_cost": decimal_string(cost_profile.overhead_cost),
            "target_margin_rate": decimal_string(cost_profile.target_margin_rate, rate=True),
        },
        competitor_context_json=competitor_context,
        created_by_user_id=actor.id,
    )
    session.add(check)
    _flush(session, code="pricing_check_conflict", detail="The pricing check could not be saved")

    for position, (strategy, margin_rate, calculated, validation) in enumerate(candidates, start=1):
        candidate = PriceCandidate(
            pricing_check_id=check.id,
            position=position,
            strategy=strategy.value,
            margin_rate=quantize_rate(margin_rate),
            is_selected=strategy == selected_strategy,
            total_cost=calculated.total_cost,
            total_price=calculated.total_price,
            estimated_gross_profit=calculated.gross_profit,
            estimated_margin_rate=calculated.margin_rate,
            notes_json=[
                "Calculated deterministically from the active V2 cost profile.",
                "No AI-generated price was used.",
            ],
        )
        session.add(candidate)
        _flush(session, code="pricing_check_conflict", detail="The pricing candidate could not be saved")
        for line, calculated_line, source_line in zip(revision_lines, calculated.lines, source_lines, strict=True):
            session.add(
                PriceCandidateLine(
                    price_candidate_id=candidate.id,
                    source_quote_revision_line_id=line.id,
                    position=line.position,
                    product_code=line.product_code,
                    quantity=line.quantity,
                    unit_cost=calculated_line.unit_cost,
                    unit_price=calculated_line.unit_price,
                    total_cost=calculated_line.total_cost,
                    total_price=calculated_line.total_price,
                    calculation_inputs_json={
                        "material_cost": decimal_string(source_line.material_cost),
                        "labor_cost": decimal_string(source_line.labor_cost),
                        "overhead_cost": decimal_string(source_line.overhead_cost),
                        "margin_rate": decimal_string(margin_rate, rate=True),
                        "unit_cost_raw": format(calculated_line.unit_cost_raw, "f"),
                        "unit_price_raw": format(calculated_line.unit_price_raw, "f"),
                        "total_cost_raw": format(calculated_line.total_cost_raw, "f"),
                        "total_price_raw": format(calculated_line.total_price_raw, "f"),
                    },
                )
            )
        result = PriceValidationResult(
            price_candidate_id=candidate.id,
            validation_status=validation.status,
            risk_level=validation.risk_level,
            minimum_margin_rate=quantize_rate(cost_profile.target_margin_rate),
        )
        session.add(result)
        _flush(session, code="pricing_check_conflict", detail="The pricing validation could not be saved")
        for validation_check in validation.checks:
            session.add(
                PriceValidationCheck(
                    price_validation_result_id=result.id,
                    code=validation_check.code,
                    severity=validation_check.severity,
                    passed=validation_check.passed,
                    message=validation_check.message,
                    details_json=validation_check.details,
                )
            )
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="pricing_check.created",
        entity_type="pricing_check",
        entity_id=str(check.id),
        request_id=request_id,
        metadata={
            "quote_id": quote.id,
            "quote_revision_id": revision.id,
            "quote_version": quote.version,
            "selected_strategy": selected_strategy.value,
            "status": check.status.value,
            "competitor_reference_count": competitor_context["reference_count"],
        },
    )
    _commit(session, code="pricing_check_conflict", detail="The pricing check could not be saved")
    return get_pricing_check(session, check.id)


def _candidate_response(session: Session, candidate: PriceCandidate) -> PriceCandidateResponse:
    result = session.scalar(
        select(PriceValidationResult).where(PriceValidationResult.price_candidate_id == candidate.id)
    )
    if result is None:
        raise RuntimeError("Pricing candidate is missing a validation result")
    validation_checks = list(
        session.scalars(
            select(PriceValidationCheck)
            .where(PriceValidationCheck.price_validation_result_id == result.id)
            .order_by(PriceValidationCheck.id.asc())
        )
    )
    lines = list(
        session.scalars(
            select(PriceCandidateLine)
            .where(PriceCandidateLine.price_candidate_id == candidate.id)
            .order_by(PriceCandidateLine.position.asc())
        )
    )
    return PriceCandidateResponse(
        id=candidate.id,
        position=candidate.position,
        strategy=PricingStrategy(candidate.strategy),
        margin_rate=decimal_string(candidate.margin_rate, rate=True),
        is_selected=candidate.is_selected,
        total_cost=decimal_string(candidate.total_cost),
        total_price=decimal_string(candidate.total_price),
        estimated_gross_profit=decimal_string(candidate.estimated_gross_profit),
        estimated_margin_rate=decimal_string(candidate.estimated_margin_rate, rate=True),
        notes=list(candidate.notes_json),
        validation=PricingValidationResponse(
            status=result.validation_status,
            risk_level=result.risk_level,
            minimum_margin_rate=decimal_string(result.minimum_margin_rate, rate=True),
            checks=[
                PricingValidationCheckResponse(
                    code=check.code,
                    severity=check.severity,
                    passed=check.passed,
                    message=check.message,
                )
                for check in validation_checks
            ],
        ),
        lines=[
            PriceCandidateLineResponse(
                id=line.id,
                position=line.position,
                product_code=line.product_code,
                quantity=line.quantity,
                unit_price=decimal_string(line.unit_price),
                total_price=decimal_string(line.total_price),
            )
            for line in lines
        ],
    )


def _competitor_context_response(context: dict[str, object]) -> CompetitorContextSummaryResponse:
    return CompetitorContextSummaryResponse(
        included=bool(context.get("included", False)),
        reference_count=int(context.get("reference_count", 0)),
        average_unit_price=context.get("average_unit_price") if isinstance(context.get("average_unit_price"), str) else None,
        source_version=str(context.get("source_version", COMPETITOR_CONTEXT_VERSION)),
        earliest_observed_at=context.get("earliest_observed_at"),
        latest_observed_at=context.get("latest_observed_at"),
    )


def _summary_response(session: Session, check: PricingCheck) -> PricingCheckSummaryResponse:
    selected = session.scalar(
        select(PriceCandidate).where(PriceCandidate.pricing_check_id == check.id, PriceCandidate.is_selected.is_(True))
    )
    if selected is None:
        raise RuntimeError("Pricing check is missing its selected candidate")
    result = session.scalar(
        select(PriceValidationResult).where(PriceValidationResult.price_candidate_id == selected.id)
    )
    if result is None:
        raise RuntimeError("Selected pricing candidate is missing its validation")
    candidate_count = int(
        session.scalar(select(func.count()).select_from(PriceCandidate).where(PriceCandidate.pricing_check_id == check.id))
        or 0
    )
    return PricingCheckSummaryResponse(
        id=check.id,
        quote_id=check.quote_id,
        quote_revision_id=check.quote_revision_id,
        quote_version=check.quote_version,
        status=check.status,
        selected_strategy=PricingStrategy(check.selected_strategy),
        selected_candidate_id=selected.id,
        selected_total_price=decimal_string(check.selected_total_price),
        selected_gross_profit=decimal_string(check.selected_gross_profit),
        selected_margin_rate=decimal_string(check.selected_margin_rate, rate=True),
        minimum_margin_rate=decimal_string(check.minimum_margin_rate, rate=True),
        candidate_count=candidate_count,
        validation_status=result.validation_status,
        risk_level=result.risk_level,
        currency=check.currency,
        formula_version=check.formula_version,
        validation_rule_version=check.validation_rule_version,
        rounding_policy_version=check.rounding_policy_version,
        created_by_user_id=check.created_by_user_id,
        created_at=check.created_at,
    )


def get_pricing_check(session: Session, pricing_check_id: int) -> PricingCheckDetailResponse:
    check = session.scalar(select(PricingCheck).where(PricingCheck.id == pricing_check_id))
    if check is None:
        raise ApiError(404, "pricing_check_not_found", "Pricing check was not found")
    summary = _summary_response(session, check)
    candidates = list(
        session.scalars(
            select(PriceCandidate)
            .where(PriceCandidate.pricing_check_id == check.id)
            .order_by(PriceCandidate.position.asc())
        )
    )
    return PricingCheckDetailResponse(
        **summary.model_dump(),
        total_cost=decimal_string(check.total_cost),
        competitor_context=_competitor_context_response(check.competitor_context_json),
        candidates=[_candidate_response(session, candidate) for candidate in candidates],
    )


def list_pricing_checks(
    session: Session, *, quote_id: int, page: int, page_size: int
) -> PricingCheckPageResponse:
    _validate_pagination(page, page_size)
    if session.scalar(select(Quote.id).where(Quote.id == quote_id)) is None:
        raise ApiError(404, "quote_not_found", "Quote was not found")
    statement = select(PricingCheck).where(PricingCheck.quote_id == quote_id)
    items = list(
        session.scalars(
            statement.order_by(PricingCheck.created_at.desc(), PricingCheck.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    total = int(session.scalar(select(func.count()).select_from(PricingCheck).where(PricingCheck.quote_id == quote_id)) or 0)
    return PricingCheckPageResponse(
        items=[_summary_response(session, check) for check in items], page=page, page_size=page_size, total=total
    )
