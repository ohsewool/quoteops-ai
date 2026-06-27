from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    DemoFullScenarioResponse,
    DemoGuideResponse,
    DemoResetResponse,
    DemoSeedResponse,
    DemoStatusResponse,
)
from backend.services.audit_service import create_audit_log
from backend.services.demo_data_service import (
    create_full_demo_scenario,
    get_demo_guide,
    get_demo_status,
    reset_demo_data,
    seed_demo_data_tools,
)


router = APIRouter(prefix="/api/demo", tags=["demo tools"])


@router.get("/status", response_model=DemoStatusResponse)
def demo_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DemoStatusResponse:
    response = get_demo_status(db)
    create_audit_log(
        db,
        action="demo_status_viewed",
        entity_type="demo",
        summary="Demo status viewed.",
        metadata={"counts": response.counts, "demo_ready": response.demo_ready},
        actor=current_user,
    )
    return response


@router.post("/seed", response_model=DemoSeedResponse, status_code=status.HTTP_201_CREATED)
def demo_seed(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> DemoSeedResponse:
    response = seed_demo_data_tools(db, current_user.username)
    create_audit_log(
        db,
        action="demo_data_seeded",
        entity_type="demo",
        summary="Deterministic demo data seeded.",
        metadata={"created_or_verified": response.created_or_verified},
        actor=current_user,
    )
    return response


@router.post("/reset", response_model=DemoResetResponse)
def demo_reset(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> DemoResetResponse:
    response = reset_demo_data(db)
    create_audit_log(
        db,
        action="demo_data_reset",
        entity_type="demo",
        summary="Known demo data reset safely.",
        metadata={"deleted_or_disabled": response.deleted_or_disabled},
        actor=current_user,
    )
    return response


@router.post(
    "/scenario/full",
    response_model=DemoFullScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def demo_full_scenario(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> DemoFullScenarioResponse:
    response = create_full_demo_scenario(db, current_user.username)
    create_audit_log(
        db,
        action="demo_full_scenario_created",
        entity_type="demo",
        summary="Full deterministic demo scenario created.",
        metadata={
            "demo_product_sku": response.demo_product_sku,
            "generated_ids": response.generated_ids,
        },
        actor=current_user,
    )
    return response


@router.get("/guide", response_model=DemoGuideResponse)
def demo_guide(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DemoGuideResponse:
    response = get_demo_guide()
    create_audit_log(
        db,
        action="demo_guide_viewed",
        entity_type="demo",
        summary="Demo guide viewed.",
        metadata={"endpoint_count": len(response.important_api_endpoints)},
        actor=current_user,
    )
    return response
