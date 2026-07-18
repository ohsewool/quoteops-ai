"""HTTP adapters for the V2 approved-Quote Report Center."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db, require_minimum_role
from backend.domain.roles import UserRole
from backend.models.user import User
from backend.schemas.html_reports import HtmlReportCreate, HtmlReportResponse
from backend.services.html_reports import (
    CONTENT_SECURITY_POLICY,
    audit_report_read,
    create_html_report,
    get_html_report,
    get_html_report_content,
    list_html_reports,
)


router = APIRouter(prefix="/api/html-reports", tags=["html reports"])


def _request_id(request: Request) -> str:
    return request.state.request_id


@router.get("", response_model=list[HtmlReportResponse])
def html_report_list(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> list[HtmlReportResponse]:
    reports = list_html_reports(db)
    audit_report_read(
        db,
        actor=actor,
        report_id=0,
        action="html_report.list_viewed",
        request_id=_request_id(request),
        metadata={"result_count": len(reports)},
    )
    return reports


@router.post("", response_model=HtmlReportResponse, status_code=status.HTTP_201_CREATED)
def html_report_create(
    payload: HtmlReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_minimum_role(UserRole.MANAGER)),
) -> HtmlReportResponse:
    return create_html_report(db, payload=payload, actor=actor, request_id=_request_id(request))


@router.get("/{report_id}", response_model=HtmlReportResponse)
def html_report_detail(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> HtmlReportResponse:
    report = get_html_report(db, report_id)
    audit_report_read(
        db,
        actor=actor,
        report_id=report.id,
        action="html_report.viewed",
        request_id=_request_id(request),
    )
    return report


@router.get("/{report_id}/content")
def html_report_content(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> Response:
    report = get_html_report_content(db, report_id)
    audit_report_read(
        db,
        actor=actor,
        report_id=report.id,
        action="html_report.content_viewed",
        request_id=_request_id(request),
    )
    return Response(
        content=report.html_content,
        media_type="text/html",
        headers={
            "Content-Security-Policy": CONTENT_SECURITY_POLICY,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'inline; filename="quoteops-report-{report.id}.html"',
        },
    )
