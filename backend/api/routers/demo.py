"""Environment-gated, admin-only guided demo HTTP adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db, get_settings, require_minimum_role
from backend.config import Settings
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.operations import DemoRunPageResponse, DemoRunResponse, DemoRunVersionedAction
from backend.services.demo import advance_demo_run, get_demo_run, list_demo_runs, reset_demo_run, start_demo_run


router = APIRouter(prefix="/api/demo", tags=["guided-demo"])


def _request_id(request: Request) -> str:
    return request.state.request_id


@router.get("/runs", response_model=DemoRunPageResponse)
def demo_runs(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> DemoRunPageResponse:
    return DemoRunPageResponse(items=list_demo_runs(db, settings=settings))


@router.post("/runs", response_model=DemoRunResponse, status_code=status.HTTP_201_CREATED)
def demo_start(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> DemoRunResponse:
    return start_demo_run(db, settings=settings, actor=actor, request_id=_request_id(request))


@router.get("/runs/{demo_run_id}", response_model=DemoRunResponse)
def demo_run_detail(
    demo_run_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> DemoRunResponse:
    return get_demo_run(db, settings=settings, demo_run_id=demo_run_id)


@router.post("/runs/{demo_run_id}/advance", response_model=DemoRunResponse)
def demo_advance(
    demo_run_id: int,
    payload: DemoRunVersionedAction,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> DemoRunResponse:
    return advance_demo_run(
        db,
        settings=settings,
        demo_run_id=demo_run_id,
        version=payload.version,
        actor=actor,
        request_id=_request_id(request),
    )


@router.post("/runs/{demo_run_id}/reset", response_model=DemoRunResponse)
def demo_reset(
    demo_run_id: int,
    payload: DemoRunVersionedAction,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> DemoRunResponse:
    return reset_demo_run(
        db,
        settings=settings,
        demo_run_id=demo_run_id,
        version=payload.version,
        actor=actor,
        request_id=_request_id(request),
    )
