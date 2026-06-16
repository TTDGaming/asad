# Asad Store · Cửa hàng số bán hàng tự động

Web app PWA bán **sản phẩm số** (tài khoản premium, key bản quyền, mã game,
khóa học...) với **giao hàng hoàn toàn tự động 24/7**. Đầy đủ 3 vai trò:
**Người dùng**, **Quản trị (Admin)** và **Tiếp thị liên kết (Affiliate)**.

Chạy trên **Windows** (trình duyệt / cài như app desktop) và **iPhone**
(Safari → *Add to Home Screen* thành app như native).

---

## ✨ Tính năng

### 👤 Người dùng
| Nhóm | Mô tả |
|---|---|
| Tài khoản | Đăng ký / đăng nhập (JWT), cập nhật hồ sơ, đổi mật khẩu. |
| Cửa hàng | Duyệt sản phẩm theo danh mục, tìm kiếm, xem chi tiết, tồn kho realtime. |
| Giỏ hàng | Thêm / sửa số lượng / xóa. |
| Thanh toán | Trừ tiền từ **ví**, **giao hàng tự động** ngay (xuất mã/key trong kho). |
| Ví điện tử | Nạp tiền tự động (giả lập cổng), lịch sử giao dịch (sổ cái số dư). |
| Đơn hàng | Lịch sử đơn, xem lại nội dung sản phẩm số đã mua. |
| Rút tiền | Gửi yêu cầu rút (Bank/Momo/ZaloPay/USDT), admin duyệt. |

### 🤝 Affiliate (tiếp thị liên kết)
- Mỗi tài khoản có **mã giới thiệu** + **link giới thiệu** riêng.
- Người đăng ký qua link được gắn vào người giới thiệu.
- Khi họ mua hàng → **hoa hồng tự động** cộng thẳng vào ví theo tỷ lệ từng sản phẩm.
- Bảng theo dõi: tổng hoa hồng, danh sách hoa hồng, người đã giới thiệu.

### ⚙️ Admin
- **Dashboard**: doanh thu, số đơn, người dùng, hoa hồng đã trả, cảnh báo sắp hết hàng, top bán chạy.
- **Sản phẩm**: CRUD, bật/tắt, hoa hồng, **quản lý kho** (nhập mã/key hàng loạt).
- **Danh mục**: CRUD.
- **Đơn hàng**: xem toàn bộ đơn.
- **Người dùng**: điều chỉnh số dư, cấp/hạ quyền admin, khóa/mở tài khoản.
- **Rút tiền**: duyệt / từ chối (tự hoàn tiền khi từ chối).
- **Cài đặt**: tên cửa hàng, khẩu hiệu, liên hệ hỗ trợ.

---

## 🚀 Chạy ở local

```bash
pip install -r requirements.txt
python run.py
```

Mặc định nghe ở `0.0.0.0:8000`.

- **Windows**: mở <http://localhost:8000>. Chrome/Edge có nút *Install app*.
- **iPhone** (cùng WiFi): mở Safari tới `http://<IP-máy>:8000` → *Share* → *Add to Home Screen*.

**Tài khoản admin mặc định**: `admin` / `admin123` (đổi qua biến môi trường
`ASAD_ADMIN_EMAIL`, `ASAD_ADMIN_PASSWORD`, hoặc đổi mật khẩu sau khi đăng nhập).
Lần chạy đầu tự tạo dữ liệu mẫu (danh mục + sản phẩm + kho hàng demo).

> Đặt biến môi trường `ASAD_SECRET` cho khóa ký JWT khi chạy production.

---

## 🧱 Cấu trúc

```
backend/
  main.py            # FastAPI app + mount frontend
  config.py          # đường dẫn, secret, admin mặc định
  database.py        # SQLAlchemy engine + session
  models.py          # User, Category, Product, ProductStock, Cart, Order,
                     #   Transaction, Commission, Withdrawal, Setting
  schemas.py         # Pydantic
  auth.py            # băm mật khẩu PBKDF2 + JWT (chỉ stdlib)
  utils.py           # slug, sinh mã, ghi sổ ví
  seed.py            # tạo admin + dữ liệu mẫu
  routers/
    auth.py          # đăng ký / đăng nhập / hồ sơ
    catalog.py       # sản phẩm + danh mục công khai + settings
    cart.py          # giỏ hàng
    orders.py        # thanh toán + giao hàng tự động + hoa hồng
    wallet.py        # nạp / rút / giao dịch
    affiliate.py     # thống kê tiếp thị liên kết
    admin.py         # toàn bộ quản trị
frontend/            # PWA (vanilla JS SPA)
  index.html  style.css  app.js
  manifest.json  sw.js  icons/
storage/             # SQLite DB (đã .gitignore)
run.py  requirements.txt
```

---

## 🔌 API tóm tắt

**Auth** · `POST /api/auth/register` · `POST /api/auth/login` · `GET/PATCH /api/auth/me`

**Cửa hàng** · `GET /api/categories` · `GET /api/products` · `GET /api/products/{slug}` · `GET /api/settings`

**Giỏ** · `GET/POST /api/cart` · `PATCH/DELETE /api/cart/{id}`

**Đơn** · `POST /api/orders/checkout` · `GET /api/orders` · `GET /api/orders/{code}`

**Ví** · `GET /api/wallet/transactions` · `POST /api/wallet/deposit` · `POST /api/wallet/withdraw` · `GET /api/wallet/withdrawals`

**Affiliate** · `GET /api/affiliate`

**Admin** · `GET /api/admin/stats` · `…/products` (+ `/{id}/stock`) · `…/categories` · `…/orders` · `…/users` (+ `/balance`) · `…/withdrawals` · `…/settings`

Xem schema đầy đủ ở `/docs` (Swagger UI).
