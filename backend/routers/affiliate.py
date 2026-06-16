from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Commission, User
from ..schemas import AffiliateStats, CommissionOut, UserOut

router = APIRouter(prefix="/api/affiliate", tags=["affiliate"])


@router.get("", response_model=AffiliateStats)
def stats(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    commissions = (
        db.query(Commission)
        .filter(Commission.affiliate_id == user.id)
        .order_by(Commission.created_at.desc())
        .all()
    )
    total_earned = (
        db.query(func.coalesce(func.sum(Commission.amount), 0.0))
        .filter(Commission.affiliate_id == user.id)
        .scalar()
        or 0.0
    )
    referrals = db.query(User).filter(User.referred_by_id == user.id).all()

    base = str(request.base_url).rstrip("/")
    return AffiliateStats(
        referral_code=user.referral_code,
        referral_link=f"{base}/?ref={user.referral_code}",
        total_referrals=len(referrals),
        total_earned=round(total_earned, 2),
        commissions=[CommissionOut.model_validate(c) for c in commissions],
        referrals=[UserOut.model_validate(r) for r in referrals],
    )
