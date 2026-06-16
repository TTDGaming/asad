from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import CartItem, Product, User
from ..schemas import CartItemIn, CartItemOut, CartItemQtyIn
from .catalog import product_out

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _serialize(db: Session, item: CartItem) -> CartItemOut:
    out = CartItemOut.model_validate(item)
    out.product = product_out(db, item.product)
    return out


@router.get("", response_model=list[CartItemOut])
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    return [_serialize(db, i) for i in items]


@router.post("", response_model=CartItemOut)
def add_to_cart(
    data: CartItemIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.get(Product, data.product_id)
    if not product or not product.is_active:
        raise HTTPException(404, "Sản phẩm không khả dụng")
    qty = max(1, data.quantity)
    item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user.id, CartItem.product_id == product.id)
        .first()
    )
    if item:
        item.quantity += qty
    else:
        item = CartItem(user_id=user.id, product_id=product.id, quantity=qty)
        db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(db, item)


@router.patch("/{item_id}", response_model=CartItemOut)
def update_qty(
    item_id: int,
    data: CartItemQtyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy mục giỏ hàng")
    if data.quantity < 1:
        db.delete(item)
        db.commit()
        raise HTTPException(204, "Đã xóa")
    item.quantity = data.quantity
    db.commit()
    db.refresh(item)
    return _serialize(db, item)


@router.delete("/{item_id}")
def remove(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy mục giỏ hàng")
    db.delete(item)
    db.commit()
    return {"ok": True}
