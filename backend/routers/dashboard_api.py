from fastapi import APIRouter

from backend.db import get_connection
from backend.schemas.dashboard import DashboardInsightsResponse, DashboardKpisResponse
from backend.services.dashboard_insights import get_dashboard_insights
from backend.services.dashboard_kpis import get_dashboard_kpis

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=DashboardKpisResponse)
def read_dashboard_kpis() -> dict:
    with get_connection() as connection:
        return get_dashboard_kpis(connection)


@router.get("/insights", response_model=DashboardInsightsResponse)
def read_dashboard_insights() -> dict:
    with get_connection() as connection:
        return get_dashboard_insights(connection)
