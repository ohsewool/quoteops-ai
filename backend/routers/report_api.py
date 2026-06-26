from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from backend.db import get_connection
from backend.routers.auth_api import require_admin_roles
from backend.services.audit_logger import audit_actor, log_audit_event
from backend.services.report_generator import (
    ReportError,
    generate_approval_report,
    generate_candidate_report,
    generate_operations_snapshot_report,
    generate_scenario_comparison_report,
    generate_validation_report,
)
from backend.services.scenario_comparison import ScenarioComparisonError


router = APIRouter(prefix="/api/reports", tags=["reports"])
READ_REPORT_ROLES = {"owner", "manager", "viewer"}


def _admin(request: Request, authorization: str | None) -> dict:
    return require_admin_roles(
        authorization,
        READ_REPORT_ROLES,
        request=request,
        action=f"{request.method} {request.url.path}",
    )


def _log_report(
    connection,
    *,
    admin: dict,
    request: Request,
    report_type: str,
    entity_type: str,
    entity_id: int | None = None,
    entity_label: str | None = None,
    metadata: dict | None = None,
) -> None:
    log_audit_event(
        connection,
        action="report_generated",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        metadata={"report_type": report_type, **(metadata or {})},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        **audit_actor(admin),
    )


@router.get("/candidate/{candidate_id}", response_class=HTMLResponse)
def candidate_report(
    candidate_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    admin = _admin(request, authorization)
    try:
        with get_connection() as connection:
            html = generate_candidate_report(connection, candidate_id)
            _log_report(
                connection,
                admin=admin,
                request=request,
                report_type="candidate_price_report",
                entity_type="candidate_table",
                entity_id=candidate_id,
                entity_label=f"Candidate table #{candidate_id}",
            )
            return HTMLResponse(content=html)
    except ReportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/validation/{candidate_id}", response_class=HTMLResponse)
def validation_report(
    candidate_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    admin = _admin(request, authorization)
    try:
        with get_connection() as connection:
            html = generate_validation_report(connection, candidate_id)
            _log_report(
                connection,
                admin=admin,
                request=request,
                report_type="validation_report",
                entity_type="candidate_table",
                entity_id=candidate_id,
                entity_label=f"Candidate table #{candidate_id}",
            )
            return HTMLResponse(content=html)
    except ReportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/scenario-comparison", response_class=HTMLResponse)
def scenario_comparison_report(
    request: Request,
    base_type: str = Query(..., pattern="^(price_table|candidate_table)$"),
    base_id: int = Query(..., ge=1),
    compare_type: str = Query(..., pattern="^(price_table|candidate_table)$"),
    compare_id: int = Query(..., ge=1),
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    admin = _admin(request, authorization)
    try:
        with get_connection() as connection:
            html = generate_scenario_comparison_report(
                connection,
                base_type=base_type,
                base_id=base_id,
                compare_type=compare_type,
                compare_id=compare_id,
            )
            _log_report(
                connection,
                admin=admin,
                request=request,
                report_type="scenario_comparison_report",
                entity_type="pricing_scenario_comparison",
                entity_label=f"{base_type} #{base_id} vs {compare_type} #{compare_id}",
                metadata={
                    "base_type": base_type,
                    "base_id": base_id,
                    "compare_type": compare_type,
                    "compare_id": compare_id,
                },
            )
            return HTMLResponse(content=html)
    except ScenarioComparisonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ReportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/approval/{candidate_id}", response_class=HTMLResponse)
def approval_report(
    candidate_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    admin = _admin(request, authorization)
    try:
        with get_connection() as connection:
            html = generate_approval_report(connection, candidate_id)
            _log_report(
                connection,
                admin=admin,
                request=request,
                report_type="approval_evidence_report",
                entity_type="candidate_table",
                entity_id=candidate_id,
                entity_label=f"Candidate table #{candidate_id}",
            )
            return HTMLResponse(content=html)
    except ReportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/operations-snapshot", response_class=HTMLResponse)
def operations_snapshot_report(
    request: Request,
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    admin = _admin(request, authorization)
    with get_connection() as connection:
        html = generate_operations_snapshot_report(connection)
        _log_report(
            connection,
            admin=admin,
            request=request,
            report_type="operations_snapshot_report",
            entity_type="operations_snapshot",
            entity_label="Operations snapshot",
        )
        return HTMLResponse(content=html)
