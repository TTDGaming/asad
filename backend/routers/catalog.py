from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category, Product, ProductStock, Setting
from ..schemas import CategoryOut, ProductOut

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/settings")
def public_settings(db: Session = Depends(get_db)):
    return {s.key: s.value for s in db.query(Setting).all()}


def product_out(db: Session, p: Product) -> ProductOut:
    stock = (
        db.query(func.count(ProductStock.id))
        .filter(ProductStock.product_id == p.id, ProductStock.is_sold.is_(False))
        .scalar()
        or 0
    )
    out = ProductOut.model_validate(p)
    out.stock_count = stock
    return out


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.get("/products", response_model=list[ProductOut])
def list_products(
    category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Product).filter(Product.is_active.is_(True))
    if category:
        cat = db.query(Category).filter(Category.slug == category).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(Product.name.ilike(like))
    products = q.order_by(Product.created_at.desc()).all()
    return [product_out(db, p) for p in products]


@router.get("/products/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.slug == slug, Product.is_active.is_(True)).first()
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    return product_out(db, p)
