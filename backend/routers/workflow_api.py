from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db import get_connection
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas.jobs import (
    AgentJob,
    AgentJobListResponse,
    AgentJobStep,
    PricingAnalysisWorkflowRequest,
    PricingAnalysisWorkflowResponse,
)
from backend.services.job_workflow import (
    JobWorkflowError,
    get_job,
    list_job_steps,
    list_jobs,
    run_pricing_analysis_workflow,
)

router = APIRouter(tags=["workflows"])


@router.post(
    "/api/workflows/pricing-analysis",
    response_model=PricingAnalysisWorkflowResponse,
)
def start_pricing_analysis_workflow(
    request: PricingAnalysisWorkflowRequest,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    with get_connection() as connection:
        return run_pricing_analysis_workflow(
            connection,
            request=request,
            admin=admin,
        )


@router.get("/api/jobs", response_model=AgentJobListResponse)
def list_agent_jobs(
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with get_connection() as connection:
        return list_jobs(
            connection,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset,
        )


@router.get("/api/jobs/{job_id}", response_model=AgentJob)
def get_agent_job(job_id: int) -> dict:
    try:
        with get_connection() as connection:
            return get_job(connection, job_id)
    except JobWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/api/jobs/{job_id}/steps", response_model=list[AgentJobStep])
def get_agent_job_steps(job_id: int) -> list[dict]:
    try:
        with get_connection() as connection:
            return list_job_steps(connection, job_id)
    except JobWorkflowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
