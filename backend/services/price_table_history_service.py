from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import (
    PriceTable,
    PriceTableItem,
    PriceTableSnapshot,
    PriceTableSnapshotItem,
)
from backend.schemas import (
    PriceTableComparisonChange,
    PriceTableComparisonResponse,
    PriceTableComparisonSummary,
    PriceTableSnapshotCreate,
    PriceTableSnapshotResponse,
    PriceTableSummaryResponse,
)


COMPARISON_NOTES = [
    "Comparison is deterministic.",
    "This comparison does not approve or activate any price.",
]


@dataclass
class ComparableItem:
    product_id: int
    product_name: str
    product_sku: str
    price: float
    margin_rate: float


def get_price_table_summary(db: Session, price_table_id: int) -> PriceTableSummaryResponse:
    price_table = _get_price_table(db, price_table_id)
    items = list(price_table.items)
    prices = [item.price for item in items]
    margins = [item.margin_rate for item in items]
    return PriceTableSummaryResponse(
        price_table_id=price_table.id,
        name=price_table.name,
        status=price_table.status,
        item_count=len(items),
        average_price=_average(prices),
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        average_margin_rate=_average(margins),
        created_at=price_table.created_at,
        updated_at=price_table.updated_at,
    )


def create_price_table_snapshot(
    db: Session,
    price_table_id: int,
    payload: PriceTableSnapshotCreate,
    created_by_username: str,
) -> PriceTableSnapshotResponse:
    price_table = _get_price_table(db, price_table_id)
    snapshot = PriceTableSnapshot(
        price_table_id=price_table.id,
        label=payload.label,
        note=payload.note,
        created_by_username=created_by_username,
    )
    db.add(snapshot)
    db.flush()
    for item in price_table.items:
        db.add(
            PriceTableSnapshotItem(
                snapshot_id=snapshot.id,
                product_id=item.product_id,
                product_name=item.product.name,
                product_sku=item.product.sku,
                price=item.price,
                margin_rate=item.margin_rate,
            )
        )
    db.commit()
    db.refresh(snapshot)
    return _snapshot_response(snapshot)


def list_price_table_snapshots(
    db: Session, price_table_id: int
) -> list[PriceTableSnapshotResponse]:
    _get_price_table(db, price_table_id)
    snapshots = (
        db.query(PriceTableSnapshot)
        .filter(PriceTableSnapshot.price_table_id == price_table_id)
        .order_by(PriceTableSnapshot.id.desc())
        .all()
    )
    return [_snapshot_response(snapshot) for snapshot in snapshots]


def get_price_table_snapshot(db: Session, snapshot_id: int) -> PriceTableSnapshotResponse:
    return _snapshot_response(_get_snapshot(db, snapshot_id))


def compare_price_tables(
    db: Session, base_price_table_id: int, target_price_table_id: int
) -> PriceTableComparisonResponse:
    base = _get_price_table(db, base_price_table_id)
    target = _get_price_table(db, target_price_table_id)
    return _compare_items(
        base_id=base.id,
        target_id=target.id,
        base_name=base.name,
        target_name=target.name,
        base_items=[_live_item(item) for item in base.items],
        target_items=[_live_item(item) for item in target.items],
    )


def compare_price_table_snapshots(
    db: Session, base_snapshot_id: int, target_snapshot_id: int
) -> PriceTableComparisonResponse:
    base = _get_snapshot(db, base_snapshot_id)
    target = _get_snapshot(db, target_snapshot_id)
    return _compare_items(
        base_id=base.id,
        target_id=target.id,
        base_name=base.label,
        target_name=target.label,
        base_items=[_snapshot_item(item) for item in base.items],
        target_items=[_snapshot_item(item) for item in target.items],
    )


def _compare_items(
    *,
    base_id: int,
    target_id: int,
    base_name: str,
    target_name: str,
    base_items: list[ComparableItem],
    target_items: list[ComparableItem],
) -> PriceTableComparisonResponse:
    base_by_product = {item.product_id: item for item in base_items}
    target_by_product = {item.product_id: item for item in target_items}
    changes: list[PriceTableComparisonChange] = []
    for product_id in sorted(set(base_by_product) | set(target_by_product)):
        base = base_by_product.get(product_id)
        target = target_by_product.get(product_id)
        display = target or base
        change_type = _change_type(base, target)
        price_delta = None
        price_delta_rate = None
        margin_delta = None
        if base and target:
            price_delta = _round_money(target.price - base.price)
            price_delta_rate = (
                round(price_delta / base.price, 4) if base.price else None
            )
            margin_delta = round(target.margin_rate - base.margin_rate, 4)
        changes.append(
            PriceTableComparisonChange(
                product_id=product_id,
                product_name=display.product_name,
                product_sku=display.product_sku,
                change_type=change_type,
                base_price=base.price if base else None,
                target_price=target.price if target else None,
                price_delta=price_delta,
                price_delta_rate=price_delta_rate,
                base_margin_rate=base.margin_rate if base else None,
                target_margin_rate=target.margin_rate if target else None,
                margin_delta=margin_delta,
            )
        )
    deltas = [change.price_delta for change in changes if change.price_delta is not None]
    delta_rates = [
        change.price_delta_rate for change in changes if change.price_delta_rate is not None
    ]
    return PriceTableComparisonResponse(
        base_id=base_id,
        target_id=target_id,
        base_name=base_name,
        target_name=target_name,
        summary=PriceTableComparisonSummary(
            added_items=sum(1 for change in changes if change.change_type == "added"),
            removed_items=sum(1 for change in changes if change.change_type == "removed"),
            changed_items=sum(1 for change in changes if change.change_type == "changed"),
            unchanged_items=sum(1 for change in changes if change.change_type == "unchanged"),
            average_price_delta=_average(deltas),
            average_price_delta_rate=_average(delta_rates),
        ),
        changes=changes,
        comparison_notes=COMPARISON_NOTES,
    )


def _change_type(
    base: ComparableItem | None, target: ComparableItem | None
) -> str:
    if base is None:
        return "added"
    if target is None:
        return "removed"
    if base.price != target.price or base.margin_rate != target.margin_rate:
        return "changed"
    return "unchanged"


def _get_price_table(db: Session, price_table_id: int) -> PriceTable:
    price_table = db.get(PriceTable, price_table_id)
    if price_table is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    return price_table


def _get_snapshot(db: Session, snapshot_id: int) -> PriceTableSnapshot:
    snapshot = db.get(PriceTableSnapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Price table snapshot not found")
    return snapshot


def _snapshot_response(snapshot: PriceTableSnapshot) -> PriceTableSnapshotResponse:
    return PriceTableSnapshotResponse(
        id=snapshot.id,
        price_table_id=snapshot.price_table_id,
        label=snapshot.label,
        note=snapshot.note,
        created_by_username=snapshot.created_by_username,
        created_at=snapshot.created_at,
        item_count=len(snapshot.items),
        items=sorted(snapshot.items, key=lambda item: item.id),
    )


def _live_item(item: PriceTableItem) -> ComparableItem:
    return ComparableItem(
        product_id=item.product_id,
        product_name=item.product.name,
        product_sku=item.product.sku,
        price=item.price,
        margin_rate=item.margin_rate,
    )


def _snapshot_item(item: PriceTableSnapshotItem) -> ComparableItem:
    return ComparableItem(
        product_id=item.product_id,
        product_name=item.product_name,
        product_sku=item.product_sku,
        price=item.price,
        margin_rate=item.margin_rate,
    )


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _round_money(value: float) -> float:
    return round(value, 2)
