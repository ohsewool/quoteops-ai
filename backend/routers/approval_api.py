from fastapi import APIRouter, HTTPException, Query

from backend.db import get_connection
from backend.schemas.approval import ApprovalRecord
from backend.services.approval_service import list_approvals

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRecord])
def get_approvals(
    candidate_table_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None),
) -> list[dict]:
    if action is not None and action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="action must be approve or reject.")

    with get_connection() as connection:
        return list_approvals(
            connection,
            candidate_table_id=candidate_table_id,
            product_id=product_id,
            action=action,
        )
