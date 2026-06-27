from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    DashboardApprovalMetrics,
    DashboardAuditMetrics,
    DashboardPricingMetrics,
    DashboardQuoteMetrics,
    DashboardResponse,
    DashboardValidationMetrics,
    DashboardWorkflowMetrics,
)
from backend.services.audit_service import create_audit_log
from backend.services.dashboard_service import (
    get_approval_metrics,
    get_audit_metrics,
    get_dashboard_metrics,
    get_pricing_metrics,
    get_quote_metrics,
    get_validation_metrics,
    get_workflow_metrics,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardResponse)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DashboardResponse:
    response = get_dashboard_metrics(db)
    create_audit_log(
        db,
        action="dashboard_summary_viewed",
        entity_type="dashboard",
        summary="Dashboard summary viewed.",
        metadata={
            "total_products": response.summary.total_products,
            "total_quote_requests": response.summary.total_quote_requests,
            "total_approval_requests": response.summary.total_approval_requests,
        },
        actor=current_user,
    )
    return response


@router.get("/metrics", response_model=DashboardResponse)
def get_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DashboardResponse:
    response = get_dashboard_metrics(db)
    create_audit_log(
        db,
        action="dashboard_metrics_viewed",
        entity_type="dashboard",
        summary="Dashboard metrics viewed.",
        metadata={"metric_groups": 6},
        actor=current_user,
    )
    return response


@router.get("/quote-metrics", response_model=DashboardQuoteMetrics)
def get_quote_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardQuoteMetrics:
    return get_quote_metrics(db)


@router.get("/approval-metrics", response_model=DashboardApprovalMetrics)
def get_approval_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardApprovalMetrics:
    return get_approval_metrics(db)


@router.get("/validation-metrics", response_model=DashboardValidationMetrics)
def get_validation_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardValidationMetrics:
    return get_validation_metrics(db)


@router.get("/pricing-metrics", response_model=DashboardPricingMetrics)
def get_pricing_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardPricingMetrics:
    return get_pricing_metrics(db)


@router.get("/workflow-metrics", response_model=DashboardWorkflowMetrics)
def get_workflow_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardWorkflowMetrics:
    return get_workflow_metrics(db)


@router.get("/audit-metrics", response_model=DashboardAuditMetrics)
def get_audit_dashboard_metrics(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> DashboardAuditMetrics:
    return get_audit_metrics(db)
