"""Safe explicit demo fixture and guide-state operations."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.errors import ApiError
from backend.config import Settings
from backend.domain.customer_requests import CustomerRequestStatus, ProductCode
from backend.domain.demo import DEMO_GUIDE_STEPS, DemoRunStatus, demo_step_count
from backend.models.customer_request import CustomerRequest
from backend.models.demo_run import DemoRun
from backend.models.pricing import CostProfile, Product
from backend.models.user import User
from backend.schemas.operations import DemoGuideStepResponse, DemoRunResponse
from backend.services.audit import append_audit_event


DEMO_PRODUCTS: tuple[tuple[ProductCode, str, int, tuple[Decimal, Decimal, Decimal, Decimal]], ...] = (
    (ProductCode.A3_FLYER, "A3 Flyer", 100, (Decimal("1000.00"), Decimal("500.00"), Decimal("500.00"), Decimal("0.350000"))),
    (ProductCode.BRAND_STICKER, "Product / Brand Sticker", 200, (Decimal("400.00"), Decimal("300.00"), Decimal("300.00"), Decimal("0.350000"))),
)


def _require_demo_enabled(settings: Settings) -> None:
    if settings.is_production_like or not settings.demo_enabled:
        raise ApiError(404, "demo_unavailable", "The guided demo is unavailable")


def _guide_for(run: DemoRun) -> DemoGuideStepResponse | None:
    if run.current_step >= demo_step_count():
        return None
    step = DEMO_GUIDE_STEPS[run.current_step]
    return DemoGuideStepResponse(index=run.current_step, total_steps=demo_step_count(), **step)


def _artifacts(run: DemoRun) -> dict[str, list[int]]:
    raw = run.artifacts_json if isinstance(run.artifacts_json, dict) else {}
    return {
        key: [int(value) for value in values if isinstance(value, int)]
        for key, values in raw.items()
        if isinstance(key, str) and isinstance(values, list)
    }


def _response(run: DemoRun) -> DemoRunResponse:
    return DemoRunResponse(
        id=run.id,
        status=run.status,
        current_step=run.current_step,
        version=run.version,
        product_codes=[item[0] for item in DEMO_PRODUCTS],
        artifacts=_artifacts(run),
        guide=_guide_for(run),
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _commit(session: Session, *, code: str, detail: str) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ApiError(409, code, detail) from error


def _active_product_or_create(session: Session, *, code: ProductCode, name: str, actor: User, request_id: str) -> tuple[Product, bool]:
    product = session.scalar(select(Product).where(Product.code == code).with_for_update())
    if product is not None:
        if not product.active:
            raise ApiError(409, "demo_product_inactive", "The required demo product is inactive")
        return product, False
    product = Product(
        code=code,
        name=name,
        description="Explicit non-production guided demo source product.",
        active=True,
        created_by_user_id=actor.id,
        version=1,
    )
    session.add(product)
    session.flush()
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="demo.product_created",
        entity_type="product",
        entity_id=str(product.id),
        request_id=request_id,
        metadata={"product_code": product.code.value},
    )
    return product, True


def _active_cost_profile_or_create(
    session: Session,
    *,
    product: Product,
    costs: tuple[Decimal, Decimal, Decimal, Decimal],
    actor: User,
    request_id: str,
) -> tuple[CostProfile, bool]:
    profile = session.scalar(
        select(CostProfile)
        .where(CostProfile.product_id == product.id, CostProfile.active.is_(True))
        .with_for_update()
    )
    if profile is not None:
        return profile, False
    material_cost, labor_cost, overhead_cost, target_margin_rate = costs
    profile = CostProfile(
        product_id=product.id,
        material_cost=material_cost,
        labor_cost=labor_cost,
        overhead_cost=overhead_cost,
        target_margin_rate=target_margin_rate,
        active=True,
        created_by_user_id=actor.id,
        version=1,
    )
    session.add(profile)
    session.flush()
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="demo.cost_profile_created",
        entity_type="cost_profile",
        entity_id=str(profile.id),
        request_id=request_id,
        metadata={"product_id": product.id},
    )
    return profile, True


def start_demo_run(session: Session, *, settings: Settings, actor: User, request_id: str) -> DemoRunResponse:
    _require_demo_enabled(settings)
    run = DemoRun(owner_user_id=actor.id, status=DemoRunStatus.READY, current_step=0, version=1, artifacts_json={})
    session.add(run)
    session.flush()

    created_product_ids: list[int] = []
    reused_product_ids: list[int] = []
    created_cost_profile_ids: list[int] = []
    customer_request_ids: list[int] = []
    for product_code, product_name, quantity, costs in DEMO_PRODUCTS:
        product, product_created = _active_product_or_create(
            session, code=product_code, name=product_name, actor=actor, request_id=request_id
        )
        profile, profile_created = _active_cost_profile_or_create(
            session, product=product, costs=costs, actor=actor, request_id=request_id
        )
        if product_created:
            created_product_ids.append(product.id)
        else:
            reused_product_ids.append(product.id)
        if profile_created:
            created_cost_profile_ids.append(profile.id)
        customer_request = CustomerRequest(
            customer_name=f"Guided demo: {product_name}",
            contact_name=None,
            product_code=product_code,
            quantity=quantity,
            due_date=None,
            notes=f"Explicit V2 guided demo run {run.id}; no credentials or external data.",
            status=CustomerRequestStatus.NEW,
            assignee_user_id=actor.id,
            created_by_user_id=actor.id,
            version=1,
        )
        session.add(customer_request)
        session.flush()
        customer_request_ids.append(customer_request.id)
        append_audit_event(
            session,
            actor_user_id=actor.id,
            action="demo.customer_request_created",
            entity_type="customer_request",
            entity_id=str(customer_request.id),
            request_id=request_id,
            metadata={"demo_run_id": run.id, "product_code": product_code.value},
        )
    run.artifacts_json = {
        "created_product_ids": created_product_ids,
        "reused_product_ids": reused_product_ids,
        "created_cost_profile_ids": created_cost_profile_ids,
        "customer_request_ids": customer_request_ids,
    }
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="demo_run.started",
        entity_type="demo_run",
        entity_id=str(run.id),
        request_id=request_id,
        metadata={"product_codes": [item[0].value for item in DEMO_PRODUCTS], "customer_request_count": len(customer_request_ids)},
    )
    _commit(session, code="demo_start_conflict", detail="The guided demo could not be started")
    session.refresh(run)
    return _response(run)


def get_demo_run(session: Session, *, settings: Settings, demo_run_id: int) -> DemoRunResponse:
    _require_demo_enabled(settings)
    run = session.scalar(select(DemoRun).where(DemoRun.id == demo_run_id))
    if run is None:
        raise ApiError(404, "demo_run_not_found", "Guided demo run was not found")
    return _response(run)


def list_demo_runs(session: Session, *, settings: Settings) -> list[DemoRunResponse]:
    _require_demo_enabled(settings)
    runs = session.scalars(select(DemoRun).order_by(DemoRun.created_at.desc(), DemoRun.id.desc()).limit(25)).all()
    return [_response(run) for run in runs]


def advance_demo_run(
    session: Session,
    *,
    settings: Settings,
    demo_run_id: int,
    version: int,
    actor: User,
    request_id: str,
) -> DemoRunResponse:
    _require_demo_enabled(settings)
    run = session.scalar(select(DemoRun).where(DemoRun.id == demo_run_id).with_for_update())
    if run is None:
        raise ApiError(404, "demo_run_not_found", "Guided demo run was not found")
    if run.version != version:
        raise ApiError(409, "stale_demo_run", "Guided demo run changed; refresh before continuing")
    if run.status is DemoRunStatus.COMPLETE:
        raise ApiError(409, "demo_run_complete", "The guided demo is already complete")
    run.current_step += 1
    run.status = DemoRunStatus.COMPLETE if run.current_step >= demo_step_count() else DemoRunStatus.IN_PROGRESS
    run.version += 1
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="demo_run.advanced",
        entity_type="demo_run",
        entity_id=str(run.id),
        request_id=request_id,
        metadata={"current_step": run.current_step, "status": run.status.value, "version": run.version},
    )
    _commit(session, code="demo_run_conflict", detail="The guided demo could not be updated")
    session.refresh(run)
    return _response(run)


def reset_demo_run(
    session: Session,
    *,
    settings: Settings,
    demo_run_id: int,
    version: int,
    actor: User,
    request_id: str,
) -> DemoRunResponse:
    _require_demo_enabled(settings)
    run = session.scalar(select(DemoRun).where(DemoRun.id == demo_run_id).with_for_update())
    if run is None:
        raise ApiError(404, "demo_run_not_found", "Guided demo run was not found")
    if run.version != version:
        raise ApiError(409, "stale_demo_run", "Guided demo run changed; refresh before resetting")
    run.current_step = 0
    run.status = DemoRunStatus.READY
    run.version += 1
    append_audit_event(
        session,
        actor_user_id=actor.id,
        action="demo_run.reset",
        entity_type="demo_run",
        entity_id=str(run.id),
        request_id=request_id,
        metadata={"guide_state_only": True, "version": run.version},
    )
    _commit(session, code="demo_run_conflict", detail="The guided demo could not be reset")
    session.refresh(run)
    return _response(run)
