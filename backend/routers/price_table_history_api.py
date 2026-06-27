from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    PriceTableCompareRequest,
    PriceTableComparisonResponse,
    PriceTableSnapshotCompareRequest,
    PriceTableSnapshotCreate,
    PriceTableSnapshotResponse,
    PriceTableSummaryResponse,
)
from backend.services.audit_service import create_audit_log
from backend.services.price_table_history_service import (
    compare_price_table_snapshots,
    compare_price_tables,
    create_price_table_snapshot,
    get_price_table_snapshot,
    get_price_table_summary,
    list_price_table_snapshots,
)


router = APIRouter(tags=["price table history"])


@router.get(
    "/api/price-tables/{price_table_id}/summary",
    response_model=PriceTableSummaryResponse,
)
def price_table_summary(
    price_table_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> PriceTableSummaryResponse:
    response = get_price_table_summary(db, price_table_id)
    create_audit_log(
        db,
        action="price_table_summary_viewed",
        entity_type="price_table",
        entity_id=price_table_id,
        summary=f"Price table {price_table_id} summary viewed.",
        metadata={"price_table_id": price_table_id, "item_count": response.item_count},
        actor=current_user,
    )
    return response


@router.post(
    "/api/price-tables/{price_table_id}/snapshots",
    response_model=PriceTableSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(
    price_table_id: int,
    payload: PriceTableSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> PriceTableSnapshotResponse:
    response = create_price_table_snapshot(db, price_table_id, payload, current_user.username)
    create_audit_log(
        db,
        action="price_table_snapshot_created",
        entity_type="price_table_snapshot",
        entity_id=response.id,
        summary=f"Price table snapshot {response.id} created.",
        metadata={"snapshot_id": response.id, "price_table_id": price_table_id, "item_count": response.item_count},
        actor=current_user,
    )
    return response


@router.get(
    "/api/price-tables/{price_table_id}/snapshots",
    response_model=list[PriceTableSnapshotResponse],
)
def list_snapshots(
    price_table_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> list[PriceTableSnapshotResponse]:
    return list_price_table_snapshots(db, price_table_id)


@router.get(
    "/api/price-table-snapshots/{snapshot_id}",
    response_model=PriceTableSnapshotResponse,
)
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("viewer")),
) -> PriceTableSnapshotResponse:
    return get_price_table_snapshot(db, snapshot_id)


@router.post("/api/price-tables/compare", response_model=PriceTableComparisonResponse)
def compare_tables(
    payload: PriceTableCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> PriceTableComparisonResponse:
    response = compare_price_tables(db, payload.base_price_table_id, payload.target_price_table_id)
    create_audit_log(
        db,
        action="price_table_comparison_created",
        entity_type="price_table",
        summary="Price table comparison created.",
        metadata={
            "base_price_table_id": payload.base_price_table_id,
            "target_price_table_id": payload.target_price_table_id,
            "changed_items": response.summary.changed_items,
        },
        actor=current_user,
    )
    return response


@router.post(
    "/api/price-table-snapshots/compare",
    response_model=PriceTableComparisonResponse,
)
def compare_snapshots(
    payload: PriceTableSnapshotCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> PriceTableComparisonResponse:
    response = compare_price_table_snapshots(db, payload.base_snapshot_id, payload.target_snapshot_id)
    create_audit_log(
        db,
        action="price_table_snapshot_comparison_created",
        entity_type="price_table_snapshot",
        summary="Price table snapshot comparison created.",
        metadata={
            "base_snapshot_id": payload.base_snapshot_id,
            "target_snapshot_id": payload.target_snapshot_id,
            "changed_items": response.summary.changed_items,
        },
        actor=current_user,
    )
    return response
