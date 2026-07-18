"""Admin diagnostics and isolated operational CSV adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db, get_settings, require_minimum_role
from backend.config import Settings
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.operations import (
    AuditEventPageResponse,
    CompetitorReferenceCsvImportRequest,
    CompetitorReferenceCsvImportResponse,
    OperationsDiagnosticsResponse,
)
from backend.services.operations import (
    export_competitor_references_csv,
    get_safe_diagnostics,
    import_competitor_references_csv,
    list_audit_events,
)


router = APIRouter(prefix="/api/operations", tags=["operations"])


def _request_id(request: Request) -> str:
    return request.state.request_id


@router.get("/diagnostics", response_model=OperationsDiagnosticsResponse)
def diagnostics(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> OperationsDiagnosticsResponse:
    return get_safe_diagnostics(db, settings=settings, actor=actor, request_id=_request_id(request))


@router.get("/audit-events", response_model=AuditEventPageResponse)
def audit_events(
    request: Request,
    page: int = 1,
    page_size: int = 25,
    action: str | None = None,
    entity_type: str | None = None,
    actor_user_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.ADMIN)),
) -> AuditEventPageResponse:
    return list_audit_events(
        db,
        page=page,
        page_size=page_size,
        action=action,
        entity_type=entity_type,
        actor_user_id=actor_user_id,
        actor=actor,
        request_id=_request_id(request),
    )


@router.post("/competitor-references/import", response_model=CompetitorReferenceCsvImportResponse)
def import_competitor_references(
    payload: CompetitorReferenceCsvImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> CompetitorReferenceCsvImportResponse:
    return import_competitor_references_csv(
        db,
        csv_text=payload.csv_text,
        actor=actor,
        request_id=_request_id(request),
    )


@router.get("/competitor-references/export", response_class=Response)
def export_competitor_references(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> Response:
    csv_text = export_competitor_references_csv(db, actor=actor, request_id=_request_id(request))
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="competitor-references-v1.csv"'},
    )
