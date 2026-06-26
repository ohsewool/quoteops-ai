from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Product
from backend.schemas import ProductCreate, ProductResponse, ProductUpdate


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    return db.query(Product).order_by(Product.id).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.active = False
    db.commit()
    db.refresh(product)
    return product
