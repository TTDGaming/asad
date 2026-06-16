from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Transaction, User, Withdrawal
from ..schemas import (
    DepositIn,
    TransactionOut,
    WithdrawalOut,
    WithdrawIn,
)
from ..utils import post_transaction

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("/transactions", response_model=list[TransactionOut])
def transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
        .all()
    )


@router.post("/deposit", response_model=TransactionOut)
def deposit(
    data: DepositIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Nạp tiền qua cổng tự động (giả lập) — cộng ngay vào ví."""
    if data.amount <= 0:
        raise HTTPException(400, "Số tiền nạp phải lớn hơn 0")
    if data.amount > 100_000_000:
        raise HTTPException(400, "Số tiền nạp vượt giới hạn")
    tx = post_transaction(db, user, "deposit", round(data.amount, 2), "Nạp ví tự động")
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/withdraw", response_model=WithdrawalOut)
def withdraw(
    data: WithdrawIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.amount <= 0:
        raise HTTPException(400, "Số tiền rút phải lớn hơn 0")
    if data.amount > user.balance:
        raise HTTPException(400, "Số dư không đủ để rút")
    if not data.account_info.strip():
        raise HTTPException(400, "Thiếu thông tin tài khoản nhận")

    # Tạm giữ tiền: trừ ngay, hoàn lại nếu admin từ chối
    post_transaction(db, user, "withdrawal", -round(data.amount, 2), "Yêu cầu rút tiền")
    w = Withdrawal(
        user_id=user.id,
        amount=round(data.amount, 2),
        method=data.method,
        account_info=data.account_info.strip(),
        status="pending",
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


@router.get("/withdrawals", response_model=list[WithdrawalOut])
def my_withdrawals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == user.id)
        .order_by(Withdrawal.created_at.desc())
        .all()
    )
