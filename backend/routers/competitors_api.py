from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Competitor, CompetitorPrice, Product
from backend.schemas import (
    CompetitorCreate,
    CompetitorPriceCreate,
    CompetitorPriceResponse,
    CompetitorResponse,
    CompetitorUpdate,
)


router = APIRouter(tags=["competitors"])


@router.get("/api/competitors", response_model=list[CompetitorResponse])
def list_competitors(db: Session = Depends(get_db)) -> list[Competitor]:
    return db.query(Competitor).order_by(Competitor.id).all()


@router.post(
    "/api/competitors",
    response_model=CompetitorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_competitor(
    payload: CompetitorCreate, db: Session = Depends(get_db)
) -> Competitor:
    competitor = Competitor(**payload.model_dump())
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return competitor


@router.get("/api/competitors/{competitor_id}", response_model=CompetitorResponse)
def get_competitor(competitor_id: int, db: Session = Depends(get_db)) -> Competitor:
    competitor = db.get(Competitor, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.put("/api/competitors/{competitor_id}", response_model=CompetitorResponse)
def update_competitor(
    competitor_id: int, payload: CompetitorUpdate, db: Session = Depends(get_db)
) -> Competitor:
    competitor = db.get(Competitor, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(competitor, field, value)
    db.commit()
    db.refresh(competitor)
    return competitor


@router.delete("/api/competitors/{competitor_id}", response_model=CompetitorResponse)
def delete_competitor(competitor_id: int, db: Session = Depends(get_db)) -> Competitor:
    competitor = db.get(Competitor, competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    competitor.active = False
    db.commit()
    db.refresh(competitor)
    return competitor


@router.get("/api/competitor-prices", response_model=list[CompetitorPriceResponse])
def list_competitor_prices(db: Session = Depends(get_db)) -> list[CompetitorPrice]:
    return db.query(CompetitorPrice).order_by(CompetitorPrice.id).all()


@router.post(
    "/api/competitor-prices",
    response_model=CompetitorPriceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_competitor_price(
    payload: CompetitorPriceCreate, db: Session = Depends(get_db)
) -> CompetitorPrice:
    if db.get(Competitor, payload.competitor_id) is None:
        raise HTTPException(status_code=404, detail="Competitor not found")
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump()
    if data["observed_at"] is None:
        data.pop("observed_at")
    competitor_price = CompetitorPrice(**data)
    db.add(competitor_price)
    db.commit()
    db.refresh(competitor_price)
    return competitor_price
