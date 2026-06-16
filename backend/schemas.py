from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----- Auth / User -----
class RegisterIn(BaseModel):
    email: str
    username: str
    password: str
    full_name: str | None = None
    referral_code: str | None = None


class LoginIn(BaseModel):
    identifier: str  # email hoặc username
    password: str


class UpdateProfileIn(BaseModel):
    full_name: str | None = None
    password: str | None = None


class UserOut(ORMModel):
    id: int
    email: str
    username: str
    full_name: str | None
    role: str
    balance: float
    referral_code: str
    referred_by_id: int | None
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ----- Category -----
class CategoryIn(BaseModel):
    name: str
    description: str | None = None
    icon: str | None = None


class CategoryOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None


# ----- Product -----
class ProductIn(BaseModel):
    name: str
    category_id: int | None = None
    description: str | None = None
    price: float = 0.0
    image_url: str | None = None
    is_active: bool = True
    auto_delivery: bool = True
    commission_rate: float = 0.1


class ProductOut(ORMModel):
    id: int
    category_id: int | None
    name: str
    slug: str
    description: str | None
    price: float
    image_url: str | None
    is_active: bool
    auto_delivery: bool
    commission_rate: float
    sold_count: int
    created_at: datetime
    stock_count: int = 0


# ----- Cart -----
class CartItemIn(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemQtyIn(BaseModel):
    quantity: int


class CartItemOut(ORMModel):
    id: int
    product_id: int
    quantity: int
    product: ProductOut


# ----- Order -----
class OrderItemOut(ORMModel):
    id: int
    product_id: int
    product_name: str
    price: float
    quantity: int
    delivered_content: str | None


class OrderOut(ORMModel):
    id: int
    code: str
    user_id: int
    total: float
    status: str
    created_at: datetime
    items: list[OrderItemOut] = []


# ----- Wallet -----
class DepositIn(BaseModel):
    amount: float


class WithdrawIn(BaseModel):
    amount: float
    method: str
    account_info: str


class TransactionOut(ORMModel):
    id: int
    type: str
    amount: float
    balance_after: float
    note: str | None
    created_at: datetime


class WithdrawalOut(ORMModel):
    id: int
    user_id: int
    amount: float
    method: str
    account_info: str
    status: str
    note: str | None
    created_at: datetime
    processed_at: datetime | None


# ----- Affiliate -----
class CommissionOut(ORMModel):
    id: int
    buyer_id: int
    order_id: int
    amount: float
    rate: float
    status: str
    created_at: datetime


class AffiliateStats(BaseModel):
    referral_code: str
    referral_link: str
    total_referrals: int
    total_earned: float
    commissions: list[CommissionOut]
    referrals: list[UserOut]


# ----- Admin -----
class StockIn(BaseModel):
    lines: str  # mỗi dòng = một mã/key


class AdjustBalanceIn(BaseModel):
    amount: float
    note: str | None = None


class UserAdminUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class WithdrawalProcessIn(BaseModel):
    status: str  # approved | rejected
    note: str | None = None


class SettingIn(BaseModel):
    key: str
    value: str
