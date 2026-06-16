from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    CartItem,
    Commission,
    Order,
    OrderItem,
    Product,
    ProductStock,
    User,
)
from ..schemas import OrderOut
from ..utils import gen_order_code, post_transaction

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkout", response_model=OrderOut)
def checkout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    if not cart:
        raise HTTPException(400, "Giỏ hàng trống")

    # 1. Kiểm tra tồn kho + tính tổng tiền
    total = 0.0
    plan = []  # (cart_item, product, [stock rows])
    for item in cart:
        product = db.get(Product, item.product_id)
        if not product or not product.is_active:
            raise HTTPException(400, f"Sản phẩm không khả dụng (#{item.product_id})")
        available = (
            db.query(ProductStock)
            .filter(ProductStock.product_id == product.id, ProductStock.is_sold.is_(False))
            .limit(item.quantity)
            .all()
        )
        if len(available) < item.quantity:
            raise HTTPException(
                400, f"'{product.name}' chỉ còn {len(available)} trong kho"
            )
        total += product.price * item.quantity
        plan.append((item, product, available))

    total = round(total, 2)
    if user.balance < total:
        raise HTTPException(
            400, f"Số dư không đủ. Cần {total:,.0f}đ, ví còn {user.balance:,.0f}đ"
        )

    # 2. Tạo đơn + trừ tiền + giao hàng tự động
    order = Order(code=gen_order_code(), user_id=user.id, total=total, status="completed")
    db.add(order)
    db.flush()

    now = datetime.utcnow()
    commission_total = 0.0
    for item, product, stocks in plan:
        delivered = []
        for s in stocks:
            s.is_sold = True
            s.sold_at = now
            delivered.append(s.content)
        product.sold_count += item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=item.quantity,
                delivered_content="\n".join(delivered),
            )
        )
        commission_total += product.price * item.quantity * (product.commission_rate or 0)
        db.delete(item)

    post_transaction(db, user, "purchase", -total, f"Thanh toán đơn {order.code}")

    # 3. Hoa hồng affiliate tự động cho người giới thiệu
    commission_total = round(commission_total, 2)
    if user.referred_by_id and commission_total > 0:
        affiliate = db.get(User, user.referred_by_id)
        if affiliate and affiliate.is_active:
            avg_rate = commission_total / total if total else 0
            db.add(
                Commission(
                    affiliate_id=affiliate.id,
                    buyer_id=user.id,
                    order_id=order.id,
                    amount=commission_total,
                    rate=round(avg_rate, 4),
                    status="paid",
                )
            )
            post_transaction(
                db, affiliate, "commission", commission_total,
                f"Hoa hồng từ đơn {order.code}",
            )

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.get("/{code}", response_model=OrderOut)
def order_detail(
    code: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.code == code).first()
    if not order or (order.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy đơn hàng")
    return order
