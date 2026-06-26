from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import CostProfile, Product
from backend.schemas import CostProfileCreate, CostProfileResponse, CostProfileUpdate


router = APIRouter(prefix="/api/cost-profiles", tags=["cost profiles"])


@router.get("", response_model=list[CostProfileResponse])
def list_cost_profiles(db: Session = Depends(get_db)) -> list[CostProfile]:
    return db.query(CostProfile).order_by(CostProfile.id).all()


@router.post("", response_model=CostProfileResponse, status_code=status.HTTP_201_CREATED)
def create_cost_profile(
    payload: CostProfileCreate, db: Session = Depends(get_db)
) -> CostProfile:
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    cost_profile = CostProfile(**payload.model_dump())
    db.add(cost_profile)
    db.commit()
    db.refresh(cost_profile)
    return cost_profile


@router.get("/{cost_profile_id}", response_model=CostProfileResponse)
def get_cost_profile(
    cost_profile_id: int, db: Session = Depends(get_db)
) -> CostProfile:
    cost_profile = db.get(CostProfile, cost_profile_id)
    if cost_profile is None:
        raise HTTPException(status_code=404, detail="Cost profile not found")
    return cost_profile


@router.put("/{cost_profile_id}", response_model=CostProfileResponse)
def update_cost_profile(
    cost_profile_id: int,
    payload: CostProfileUpdate,
    db: Session = Depends(get_db),
) -> CostProfile:
    cost_profile = db.get(CostProfile, cost_profile_id)
    if cost_profile is None:
        raise HTTPException(status_code=404, detail="Cost profile not found")
    data = payload.model_dump(exclude_unset=True)
    if "product_id" in data and db.get(Product, data["product_id"]) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in data.items():
        setattr(cost_profile, field, value)
    db.commit()
    db.refresh(cost_profile)
    return cost_profile


@router.delete("/{cost_profile_id}", response_model=CostProfileResponse)
def delete_cost_profile(
    cost_profile_id: int, db: Session = Depends(get_db)
) -> CostProfile:
    cost_profile = db.get(CostProfile, cost_profile_id)
    if cost_profile is None:
        raise HTTPException(status_code=404, detail="Cost profile not found")
    cost_profile.active = False
    db.commit()
    db.refresh(cost_profile)
    return cost_profile
