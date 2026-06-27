import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import WorkflowJob
from backend.schemas import (
    CandidatePriceRequest,
    CustomerQuoteCandidatePriceRequest,
    PriceValidationRequest,
    PricingSimulationCreate,
    WorkflowJobCreate,
    WorkflowJobResponse,
)
from backend.services.candidate_price_service import generate_candidate_prices
from backend.services.customer_quote_request_service import (
    candidate_prices_from_request,
    get_customer_quote_request,
    quote_preview_from_request,
)
from backend.services.pricing_simulation_service import create_pricing_simulation
from backend.services.validation_service import validate_price


ALLOWED_JOB_TYPES = {"pricing_simulation", "price_validation_batch", "quote_request_review"}
WORKFLOW_NOTES = [
    "Workflow job created.",
    "No AI-generated price was used.",
    "This job does not approve or activate prices.",
]


def create_workflow_job(
    db: Session, payload: WorkflowJobCreate, created_by_username: str
) -> WorkflowJobResponse:
    if payload.job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported workflow job type")
    job = WorkflowJob(
        job_type=payload.job_type,
        title=payload.title,
        description=payload.description,
        input_json=_json(payload.input),
        created_by_username=created_by_username,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_response(job)


def list_workflow_jobs(
    db: Session,
    *,
    job_type: str | None = None,
    status: str | None = None,
    created_by_username: str | None = None,
    limit: int = 50,
) -> list[WorkflowJobResponse]:
    query = db.query(WorkflowJob)
    if job_type:
        query = query.filter(WorkflowJob.job_type == job_type)
    if status:
        query = query.filter(WorkflowJob.status == status)
    if created_by_username:
        query = query.filter(WorkflowJob.created_by_username == created_by_username)
    safe_limit = min(max(limit, 1), 100)
    jobs = query.order_by(WorkflowJob.id.desc()).limit(safe_limit).all()
    return [_to_response(job) for job in jobs]


def get_workflow_job(db: Session, job_id: int) -> WorkflowJobResponse:
    return _to_response(_get_job(db, job_id))


def run_workflow_job(db: Session, job_id: int) -> WorkflowJobResponse:
    job = _get_job(db, job_id)
    if job.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending jobs can be run")
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()
    try:
        result = _run_job_logic(db, job)
        job.status = "completed"
        job.result_json = _json(result)
        job.error_message = None
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:500]
    job.completed_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return _to_response(job)


def cancel_workflow_job(db: Session, job_id: int) -> WorkflowJobResponse:
    job = _get_job(db, job_id)
    if job.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending jobs can be cancelled")
    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return _to_response(job)


def _run_job_logic(db: Session, job: WorkflowJob) -> dict[str, Any]:
    payload = _loads(job.input_json)
    if job.job_type == "pricing_simulation":
        simulation = create_pricing_simulation(
            db,
            PricingSimulationCreate(
                name=job.title,
                product_id=payload["product_id"],
                quantities=payload["quantities"],
                margin_rates=payload["margin_rates"],
                include_competitor_context=payload.get("include_competitor_context", False),
                notes=job.description,
            ),
            job.created_by_username,
        )
        return {
            "simulation_id": simulation.id,
            "scenario_count": simulation.scenario_count,
            "product_id": simulation.product_id,
            "unit_cost": simulation.unit_cost,
        }
    if job.job_type == "price_validation_batch":
        items = payload.get("items", [])
        results = []
        counts = {"passed": 0, "warning": 0, "failed": 0}
        for item in items:
            validation = validate_price(
                db,
                PriceValidationRequest(
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    candidate_unit_price=item["candidate_unit_price"],
                    minimum_margin_rate=item.get("minimum_margin_rate"),
                    include_competitor_context=item.get("include_competitor_context", False),
                ),
            )
            counts[validation.validation_status] += 1
            results.append(
                {
                    "product_id": validation.product_id,
                    "quantity": validation.quantity,
                    "candidate_unit_price": validation.candidate_unit_price,
                    "validation_status": validation.validation_status,
                    "risk_level": validation.risk_level,
                }
            )
        return {"item_count": len(results), "summary": counts, "items": results}
    if job.job_type == "quote_request_review":
        request_id = payload["customer_quote_request_id"]
        quote_request = get_customer_quote_request(db, request_id)
        result: dict[str, Any] = {
            "customer_quote_request_id": quote_request.id,
            "status": quote_request.status,
            "product_id": quote_request.product_id,
            "quantity": quote_request.quantity,
        }
        if payload.get("include_quote_preview", False):
            preview = quote_preview_from_request(db, request_id)
            result["quote_preview"] = {
                "suggested_unit_price": preview.suggested_unit_price,
                "suggested_total_price": preview.suggested_total_price,
                "estimated_margin_rate": preview.estimated_margin_rate,
            }
        if payload.get("include_candidate_prices", False):
            candidates = candidate_prices_from_request(
                db,
                request_id,
                CustomerQuoteCandidatePriceRequest(
                    margin_rates=payload.get("margin_rates"),
                    include_competitor_context=payload.get("include_competitor_context", False),
                ),
            )
            result["candidate_prices"] = {
                "candidate_count": len(candidates.candidates),
                "strategies": [candidate.strategy for candidate in candidates.candidates],
            }
        return result
    raise HTTPException(status_code=400, detail="Unsupported workflow job type")


def _get_job(db: Session, job_id: int) -> WorkflowJob:
    job = db.get(WorkflowJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Workflow job not found")
    return job


def _to_response(job: WorkflowJob) -> WorkflowJobResponse:
    return WorkflowJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        title=job.title,
        description=job.description,
        input=_loads(job.input_json),
        result=_loads(job.result_json) if job.result_json else None,
        error_message=job.error_message,
        created_by_username=job.created_by_username,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        workflow_notes=WORKFLOW_NOTES,
    )


def _json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _loads(value: str) -> dict:
    return json.loads(value)
