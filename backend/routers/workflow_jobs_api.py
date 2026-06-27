from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import WorkflowJobCreate, WorkflowJobResponse
from backend.services.audit_service import create_audit_log
from backend.services.workflow_job_service import (
    cancel_workflow_job,
    create_workflow_job,
    get_workflow_job,
    list_workflow_jobs,
    run_workflow_job,
)


router = APIRouter(prefix="/api/workflow-jobs", tags=["workflow jobs"])


@router.post("", response_model=WorkflowJobResponse, status_code=201)
def create_job(
    payload: WorkflowJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> WorkflowJobResponse:
    response = create_workflow_job(db, payload, current_user.username)
    create_audit_log(
        db,
        action="workflow_job_created",
        entity_type="workflow_job",
        entity_id=response.id,
        summary=f"Workflow job {response.id} created.",
        metadata={"job_id": response.id, "job_type": response.job_type, "status": response.status},
        actor=current_user,
    )
    return response


@router.get("", response_model=list[WorkflowJobResponse])
def list_jobs(
    job_type: str | None = None,
    status: str | None = None,
    created_by_username: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> list[WorkflowJobResponse]:
    response = list_workflow_jobs(
        db,
        job_type=job_type,
        status=status,
        created_by_username=created_by_username,
        limit=limit,
    )
    create_audit_log(
        db,
        action="workflow_job_viewed",
        entity_type="workflow_job",
        summary="Workflow jobs list viewed.",
        metadata={"result_count": len(response)},
        actor=current_user,
    )
    return response


@router.get("/{job_id}", response_model=WorkflowJobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> WorkflowJobResponse:
    response = get_workflow_job(db, job_id)
    create_audit_log(
        db,
        action="workflow_job_viewed",
        entity_type="workflow_job",
        entity_id=response.id,
        summary=f"Workflow job {response.id} viewed.",
        metadata={"job_id": response.id, "job_type": response.job_type, "status": response.status},
        actor=current_user,
    )
    return response


@router.post("/{job_id}/run", response_model=WorkflowJobResponse)
def run_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> WorkflowJobResponse:
    started = get_workflow_job(db, job_id)
    if started.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending jobs can be run")
    create_audit_log(
        db,
        action="workflow_job_started",
        entity_type="workflow_job",
        entity_id=started.id,
        summary=f"Workflow job {started.id} started.",
        metadata={"job_id": started.id, "job_type": started.job_type},
        actor=current_user,
    )
    response = run_workflow_job(db, job_id)
    create_audit_log(
        db,
        action="workflow_job_completed" if response.status == "completed" else "workflow_job_failed",
        entity_type="workflow_job",
        entity_id=response.id,
        summary=f"Workflow job {response.id} finished with status {response.status}.",
        metadata={"job_id": response.id, "job_type": response.job_type, "status": response.status},
        actor=current_user,
    )
    return response


@router.post("/{job_id}/cancel", response_model=WorkflowJobResponse)
def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> WorkflowJobResponse:
    response = cancel_workflow_job(db, job_id)
    create_audit_log(
        db,
        action="workflow_job_cancelled",
        entity_type="workflow_job",
        entity_id=response.id,
        summary=f"Workflow job {response.id} cancelled.",
        metadata={"job_id": response.id, "job_type": response.job_type, "status": response.status},
        actor=current_user,
    )
    return response
