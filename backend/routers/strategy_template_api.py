from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db import get_connection
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas.strategy_template import (
    StrategyTemplate,
    StrategyTemplateCreate,
    StrategyTemplateUpdate,
)
from backend.services.audit_logger import log_audit_event
from backend.services.strategy_templates import (
    StrategyTemplateError,
    archive_strategy_template,
    create_strategy_template,
    get_strategy_template,
    list_product_strategy_templates,
    list_strategy_templates,
    update_strategy_template,
)

router = APIRouter(prefix="/api", tags=["strategy-templates"])


@router.get("/strategy-templates", response_model=list[StrategyTemplate])
def list_templates(
    product_id: int | None = Query(default=None, ge=1),
    product_category_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
) -> list[dict]:
    with get_connection() as connection:
        return list_strategy_templates(
            connection,
            product_id=product_id,
            product_category_id=product_category_id,
            is_active=is_active,
        )


@router.get("/products/{product_id}/strategy-templates", response_model=list[StrategyTemplate])
def list_templates_for_product(product_id: int) -> list[dict]:
    try:
        with get_connection() as connection:
            return list_product_strategy_templates(connection, product_id=product_id)
    except StrategyTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/strategy-templates/{template_id}", response_model=StrategyTemplate)
def get_template(template_id: int) -> dict:
    try:
        with get_connection() as connection:
            return get_strategy_template(connection, template_id)
    except StrategyTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/strategy-templates", response_model=StrategyTemplate, status_code=201)
def create_template(
    request: StrategyTemplateCreate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            template = create_strategy_template(connection, request.model_dump())
            log_audit_event(
                connection,
                action="strategy_template_created",
                entity_type="strategy_template",
                entity_id=template["id"],
                entity_label=template["name"],
                after=template,
            )
            return template
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Strategy template slug must be unique.") from exc
    except StrategyTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/strategy-templates/{template_id}", response_model=StrategyTemplate)
def update_template(
    template_id: int,
    request: StrategyTemplateUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            before = get_strategy_template(connection, template_id)
            template = update_strategy_template(
                connection,
                template_id,
                request.model_dump(exclude_unset=True),
            )
            log_audit_event(
                connection,
                action="strategy_template_updated",
                entity_type="strategy_template",
                entity_id=template_id,
                entity_label=template["name"],
                before=before,
                after=template,
            )
            return template
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Strategy template slug must be unique.") from exc
    except StrategyTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/strategy-templates/{template_id}", response_model=StrategyTemplate)
def archive_template(
    template_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    try:
        with get_connection() as connection:
            before = get_strategy_template(connection, template_id)
            template = archive_strategy_template(connection, template_id)
            log_audit_event(
                connection,
                action="strategy_template_archived",
                entity_type="strategy_template",
                entity_id=template_id,
                entity_label=template["name"],
                before=before,
                after=template,
            )
            return template
    except StrategyTemplateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
