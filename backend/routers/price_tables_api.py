from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import PriceTable, PriceTableItem, Product
from backend.schemas import (
    PriceTableCreate,
    PriceTableItemCreate,
    PriceTableItemResponse,
    PriceTableResponse,
    PriceTableUpdate,
)


router = APIRouter(prefix="/api/price-tables", tags=["price tables"])


@router.get("", response_model=list[PriceTableResponse])
def list_price_tables(db: Session = Depends(get_db)) -> list[PriceTable]:
    return db.query(PriceTable).order_by(PriceTable.id).all()


@router.post("", response_model=PriceTableResponse, status_code=status.HTTP_201_CREATED)
def create_price_table(
    payload: PriceTableCreate, db: Session = Depends(get_db)
) -> PriceTable:
    price_table = PriceTable(**payload.model_dump())
    db.add(price_table)
    db.commit()
    db.refresh(price_table)
    return price_table


@router.get("/{price_table_id}", response_model=PriceTableResponse)
def get_price_table(price_table_id: int, db: Session = Depends(get_db)) -> PriceTable:
    price_table = db.get(PriceTable, price_table_id)
    if price_table is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    return price_table


@router.put("/{price_table_id}", response_model=PriceTableResponse)
def update_price_table(
    price_table_id: int, payload: PriceTableUpdate, db: Session = Depends(get_db)
) -> PriceTable:
    price_table = db.get(PriceTable, price_table_id)
    if price_table is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(price_table, field, value)
    db.commit()
    db.refresh(price_table)
    return price_table


@router.delete("/{price_table_id}", response_model=PriceTableResponse)
def delete_price_table(price_table_id: int, db: Session = Depends(get_db)) -> PriceTable:
    price_table = db.get(PriceTable, price_table_id)
    if price_table is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    price_table.status = "archived"
    db.commit()
    db.refresh(price_table)
    return price_table


@router.get("/{price_table_id}/items", response_model=list[PriceTableItemResponse])
def list_price_table_items(
    price_table_id: int, db: Session = Depends(get_db)
) -> list[PriceTableItem]:
    if db.get(PriceTable, price_table_id) is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    return (
        db.query(PriceTableItem)
        .filter(PriceTableItem.price_table_id == price_table_id)
        .order_by(PriceTableItem.id)
        .all()
    )


@router.post(
    "/{price_table_id}/items",
    response_model=PriceTableItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_table_item(
    price_table_id: int,
    payload: PriceTableItemCreate,
    db: Session = Depends(get_db),
) -> PriceTableItem:
    if db.get(PriceTable, price_table_id) is None:
        raise HTTPException(status_code=404, detail="Price table not found")
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    price_table_item = PriceTableItem(
        price_table_id=price_table_id,
        **payload.model_dump(),
    )
    db.add(price_table_item)
    db.commit()
    db.refresh(price_table_item)
    return price_table_item
