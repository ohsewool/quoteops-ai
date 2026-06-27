from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import DashboardInsightRulesResponse, DashboardInsightsResponse
from backend.services.audit_service import create_audit_log
from backend.services.dashboard_insights_service import (
    get_dashboard_insight_rules,
    get_dashboard_insights,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/insights", response_model=DashboardInsightsResponse)
def get_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DashboardInsightsResponse:
    response = get_dashboard_insights(db)
    create_audit_log(
        db,
        action="dashboard_insights_viewed",
        entity_type="dashboard",
        summary="Dashboard insights viewed.",
        metadata={
            "insight_count": response.insight_count,
            "warning_or_critical_count": sum(
                1
                for insight in response.insights
                if insight.severity in {"warning", "critical"}
            ),
        },
        actor=current_user,
    )
    return response


@router.get("/insights/rules", response_model=DashboardInsightRulesResponse)
def get_insight_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> DashboardInsightRulesResponse:
    response = get_dashboard_insight_rules()
    create_audit_log(
        db,
        action="dashboard_insight_rules_viewed",
        entity_type="dashboard",
        summary="Dashboard insight rules viewed.",
        metadata={"rule_count": len(response.rules)},
        actor=current_user,
    )
    return response
