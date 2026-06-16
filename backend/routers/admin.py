from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import (
    Category,
    Commission,
    Order,
    Product,
    ProductStock,
    Setting,
    Transaction,
    User,
    Withdrawal,
)
from ..schemas import (
    AdjustBalanceIn,
    CategoryIn,
    CategoryOut,
    OrderOut,
    ProductIn,
    ProductOut,
    SettingIn,
    StockIn,
    UserAdminUpdate,
    UserOut,
    WithdrawalOut,
    WithdrawalProcessIn,
)
from ..utils import post_transaction, unique_slug
from .catalog import product_out

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- Dashboard ----------
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    revenue = (
        db.query(func.coalesce(func.sum(Order.total), 0.0))
        .filter(Order.status == "completed")
        .scalar()
        or 0.0
    )
    low_stock = []
    for p in db.query(Product).filter(Product.is_active.is_(True)).all():
        cnt = (
            db.query(func.count(ProductStock.id))
            .filter(ProductStock.product_id == p.id, ProductStock.is_sold.is_(False))
            .scalar()
            or 0
        )
        if cnt <= 3:
            low_stock.append({"id": p.id, "name": p.name, "stock": cnt})
    top = (
        db.query(Product)
        .order_by(Product.sold_count.desc())
        .limit(5)
        .all()
    )
    return {
        "users": db.query(func.count(User.id)).scalar(),
        "products": db.query(func.count(Product.id)).scalar(),
        "orders": db.query(func.count(Order.id)).scalar(),
        "revenue": round(revenue, 2),
        "pending_withdrawals": db.query(func.count(Withdrawal.id))
        .filter(Withdrawal.status == "pending")
        .scalar(),
        "commissions_paid": round(
            db.query(func.coalesce(func.sum(Commission.amount), 0.0)).scalar() or 0.0, 2
        ),
        "low_stock": low_stock,
        "top_products": [
            {"name": p.name, "sold": p.sold_count, "revenue": round(p.sold_count * p.price, 2)}
            for p in top
        ],
    }


# ---------- Categories ----------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories", response_model=CategoryOut)
def create_category(data: CategoryIn, db: Session = Depends(get_db)):
    cat = Category(
        name=data.name,
        slug=unique_slug(db, Category, data.name),
        description=data.description,
        icon=data.icon,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.patch("/categories/{cid}", response_model=CategoryOut)
def update_category(cid: int, data: CategoryIn, db: Session = Depends(get_db)):
    cat = db.get(Category, cid)
    if not cat:
        raise HTTPException(404, "Không tìm thấy danh mục")
    cat.name = data.name
    cat.description = data.description
    cat.icon = data.icon
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cid}")
def delete_category(cid: int, db: Session = Depends(get_db)):
    cat = db.get(Category, cid)
    if not cat:
        raise HTTPException(404, "Không tìm thấy danh mục")
    db.query(Product).filter(Product.category_id == cid).update({Product.category_id: None})
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ---------- Products ----------
@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.created_at.desc()).all()
    return [product_out(db, p) for p in products]


@router.post("/products", response_model=ProductOut)
def create_product(data: ProductIn, db: Session = Depends(get_db)):
    p = Product(
        name=data.name,
        slug=unique_slug(db, Product, data.name),
        category_id=data.category_id,
        description=data.description,
        price=data.price,
        image_url=data.image_url,
        is_active=data.is_active,
        auto_delivery=data.auto_delivery,
        commission_rate=data.commission_rate,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return product_out(db, p)


@router.patch("/products/{pid}", response_model=ProductOut)
def update_product(pid: int, data: ProductIn, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    p.name = data.name
    p.category_id = data.category_id
    p.description = data.description
    p.price = data.price
    p.image_url = data.image_url
    p.is_active = data.is_active
    p.auto_delivery = data.auto_delivery
    p.commission_rate = data.commission_rate
    db.commit()
    db.refresh(p)
    return product_out(db, p)


@router.delete("/products/{pid}")
def delete_product(pid: int, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.get("/products/{pid}/stock")
def get_stock(pid: int, db: Session = Depends(get_db)):
    rows = db.query(ProductStock).filter(ProductStock.product_id == pid).all()
    return {
        "available": [{"id": r.id, "content": r.content} for r in rows if not r.is_sold],
        "sold": sum(1 for r in rows if r.is_sold),
    }


@router.post("/products/{pid}/stock")
def add_stock(pid: int, data: StockIn, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p:
        raise HTTPException(404, "Không tìm thấy sản phẩm")
    lines = [ln.strip() for ln in data.lines.splitlines() if ln.strip()]
    for line in lines:
        db.add(ProductStock(product_id=pid, content=line))
    db.commit()
    return {"added": len(lines)}


@router.delete("/stock/{sid}")
def delete_stock(sid: int, db: Session = Depends(get_db)):
    s = db.get(ProductStock, sid)
    if not s or s.is_sold:
        raise HTTPException(404, "Không tìm thấy mã còn trống")
    db.delete(s)
    db.commit()
    return {"ok": True}


# ---------- Orders ----------
@router.get("/orders", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc()).limit(200).all()


# ---------- Users ----------
@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{uid}", response_model=UserOut)
def update_user(uid: int, data: UserAdminUpdate, db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if data.role in ("user", "admin"):
        u.role = data.role
    if data.is_active is not None:
        u.is_active = data.is_active
    db.commit()
    db.refresh(u)
    return u


@router.post("/users/{uid}/balance", response_model=UserOut)
def adjust_balance(uid: int, data: AdjustBalanceIn, db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if u.balance + data.amount < 0:
        raise HTTPException(400, "Số dư không thể âm")
    post_transaction(db, u, "adjust", round(data.amount, 2), data.note or "Admin điều chỉnh")
    db.commit()
    db.refresh(u)
    return u


# ---------- Withdrawals ----------
@router.get("/withdrawals", response_model=list[WithdrawalOut])
def list_withdrawals(db: Session = Depends(get_db)):
    return db.query(Withdrawal).order_by(Withdrawal.created_at.desc()).all()


@router.post("/withdrawals/{wid}", response_model=WithdrawalOut)
def process_withdrawal(wid: int, data: WithdrawalProcessIn, db: Session = Depends(get_db)):
    w = db.get(Withdrawal, wid)
    if not w:
        raise HTTPException(404, "Không tìm thấy yêu cầu")
    if w.status != "pending":
        raise HTTPException(400, "Yêu cầu đã được xử lý")
    if data.status not in ("approved", "rejected"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    w.status = data.status
    w.note = data.note
    w.processed_at = datetime.utcnow()
    if data.status == "rejected":
        # hoàn lại tiền đã tạm giữ
        user = db.get(User, w.user_id)
        post_transaction(db, user, "refund", w.amount, f"Hoàn rút tiền #{w.id}")
    db.commit()
    db.refresh(w)
    return w


# ---------- Settings ----------
@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {s.key: s.value for s in db.query(Setting).all()}


@router.put("/settings")
def set_setting(data: SettingIn, db: Session = Depends(get_db)):
    s = db.get(Setting, data.key)
    if s:
        s.value = data.value
    else:
        db.add(Setting(key=data.key, value=data.value))
    db.commit()
    return {"ok": True}
