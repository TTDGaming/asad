from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UpdateProfileIn, UserOut
from ..utils import gen_referral_code

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    username = data.username.strip()
    if not email or "@" not in email:
        raise HTTPException(400, "Email không hợp lệ")
    if len(username) < 3:
        raise HTTPException(400, "Tên đăng nhập tối thiểu 3 ký tự")
    if len(data.password) < 6:
        raise HTTPException(400, "Mật khẩu tối thiểu 6 ký tự")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email đã được đăng ký")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Tên đăng nhập đã tồn tại")

    referrer = None
    if data.referral_code:
        referrer = (
            db.query(User)
            .filter(User.referral_code == data.referral_code.strip().upper())
            .first()
        )

    user = User(
        email=email,
        username=username,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        referral_code=gen_referral_code(db),
        referred_by_id=referrer.id if referrer else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    ident = data.identifier.strip().lower()
    user = (
        db.query(User)
        .filter((User.email == ident) | (User.username == data.identifier.strip()))
        .first()
    )
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Sai thông tin đăng nhập")
    if not user.is_active:
        raise HTTPException(403, "Tài khoản đã bị khóa")
    return TokenOut(token=create_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UpdateProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.password:
        if len(data.password) < 6:
            raise HTTPException(400, "Mật khẩu tối thiểu 6 ký tự")
        user.password_hash = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user
