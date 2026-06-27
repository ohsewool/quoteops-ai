from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import HtmlReportCreate, HtmlReportResponse
from backend.services.audit_service import create_audit_log
from backend.services.html_report_service import (
    create_html_report,
    get_html_report,
    get_html_report_content,
    list_html_reports,
)


router = APIRouter(prefix="/api/html-reports", tags=["html reports"])


@router.post("", response_model=HtmlReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: HtmlReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> HtmlReportResponse:
    response = create_html_report(db, payload, current_user.username)
    create_audit_log(
        db,
        action="html_report_created",
        entity_type="html_report",
        entity_id=response.id,
        summary=f"HTML report {response.id} created.",
        metadata={
            "report_id": response.id,
            "report_type": response.report_type,
            "source_type": response.source_type,
            "source_id": response.source_id,
        },
        actor=current_user,
    )
    return response


@router.get("", response_model=list[HtmlReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> list[HtmlReportResponse]:
    response = list_html_reports(db)
    create_audit_log(
        db,
        action="html_report_list_viewed",
        entity_type="html_report",
        summary="HTML report list viewed.",
        metadata={"result_count": len(response)},
        actor=current_user,
    )
    return response


@router.get("/{report_id}", response_model=HtmlReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> HtmlReportResponse:
    response = get_html_report(db, report_id)
    create_audit_log(
        db,
        action="html_report_viewed",
        entity_type="html_report",
        entity_id=response.id,
        summary=f"HTML report {response.id} viewed.",
        metadata={"report_id": response.id, "report_type": response.report_type},
        actor=current_user,
    )
    return response


@router.get("/{report_id}/content")
def get_report_content(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> Response:
    content = get_html_report_content(db, report_id)
    create_audit_log(
        db,
        action="html_report_content_viewed",
        entity_type="html_report",
        entity_id=report_id,
        summary=f"HTML report {report_id} content viewed.",
        metadata={"report_id": report_id},
        actor=current_user,
    )
    return Response(content=content, media_type="text/html; charset=utf-8")
