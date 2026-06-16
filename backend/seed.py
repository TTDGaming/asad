"""Khởi tạo dữ liệu lần đầu: tài khoản admin + danh mục, sản phẩm, kho hàng mẫu."""
from .auth import hash_password
from .config import ADMIN_EMAIL, ADMIN_PASSWORD
from .database import SessionLocal
from .models import Category, Product, ProductStock, Setting, User
from .utils import gen_referral_code, slugify


def seed():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "admin").first():
            admin = User(
                email=ADMIN_EMAIL,
                username="admin",
                full_name="Quản trị viên",
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
                balance=0.0,
                referral_code=gen_referral_code(db),
            )
            db.add(admin)

        defaults = {
            "site_name": "Asad Store",
            "site_tagline": "Cửa hàng số tự động — giao hàng tức thì 24/7",
            "support_contact": "Telegram: @asad_support",
        }
        for k, v in defaults.items():
            if not db.get(Setting, k):
                db.add(Setting(key=k, value=v))

        if not db.query(Category).first():
            cat_data = [
                ("Tài khoản Premium", "🎬", "Netflix, Spotify, YouTube Premium..."),
                ("Phần mềm bản quyền", "💻", "Key Windows, Office, antivirus..."),
                ("Game & Steam", "🎮", "Key game, nạp game, tài khoản Steam..."),
                ("Khóa học online", "📚", "Khóa học kỹ năng, ngoại ngữ, lập trình..."),
            ]
            cats = {}
            for name, icon, desc in cat_data:
                c = Category(name=name, slug=slugify(name), icon=icon, description=desc)
                db.add(c)
                db.flush()
                cats[name] = c

            prod_data = [
                ("Tài khoản Premium", "Netflix Premium 1 tháng 4K", 59000, 0.1,
                 "Tài khoản Netflix gói Premium xem 4K, bảo hành 30 ngày."),
                ("Tài khoản Premium", "Spotify Premium 1 năm", 199000, 0.12,
                 "Nâng cấp chính chủ tài khoản của bạn, nghe nhạc không quảng cáo."),
                ("Phần mềm bản quyền", "Windows 11 Pro Key bản quyền", 149000, 0.15,
                 "Key kích hoạt Windows 11 Pro vĩnh viễn, hỗ trợ cài đặt."),
                ("Phần mềm bản quyền", "Microsoft Office 2021 Pro Plus", 179000, 0.15,
                 "Key Office 2021 bản quyền vĩnh viễn cho 1 PC."),
                ("Game & Steam", "Steam Wallet 100.000đ", 95000, 0.05,
                 "Mã nạp ví Steam, giao tự động ngay sau thanh toán."),
                ("Khóa học online", "Combo khóa học Python từ A-Z", 299000, 0.2,
                 "Trọn bộ tài liệu + video khóa học lập trình Python."),
            ]
            for cat_name, name, price, rate, desc in prod_data:
                p = Product(
                    name=name,
                    slug=slugify(name),
                    category_id=cats[cat_name].id,
                    description=desc,
                    price=price,
                    commission_rate=rate,
                    image_url=None,
                )
                db.add(p)
                db.flush()
                for i in range(1, 11):
                    db.add(
                        ProductStock(
                            product_id=p.id,
                            content=f"{slugify(name).upper()}-DEMO-KEY-{i:03d}",
                        )
                    )

        db.commit()
    finally:
        db.close()
