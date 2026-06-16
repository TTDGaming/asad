import re
import secrets
import unicodedata

from sqlalchemy.orm import Session

from .models import Transaction, User


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "item"


def unique_slug(db: Session, model, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    i = 2
    while db.query(model).filter(model.slug == candidate).first():
        candidate = f"{slug}-{i}"
        i += 1
    return candidate


def gen_referral_code(db: Session) -> str:
    while True:
        code = secrets.token_hex(4).upper()
        if not db.query(User).filter(User.referral_code == code).first():
            return code


def gen_order_code() -> str:
    return "DH" + secrets.token_hex(4).upper()


def post_transaction(
    db: Session, user: User, type_: str, amount: float, note: str | None = None
) -> Transaction:
    """Cập nhật số dư ví và ghi một dòng sổ cái. amount âm = trừ tiền."""
    user.balance = round(user.balance + amount, 2)
    tx = Transaction(
        user_id=user.id,
        type=type_,
        amount=amount,
        balance_after=user.balance,
        note=note,
    )
    db.add(tx)
    return tx
