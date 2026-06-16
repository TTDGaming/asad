import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "app.db"
FRONTEND_DIR = BASE_DIR / "frontend"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# Bí mật ký JWT. Trong production đặt qua biến môi trường ASAD_SECRET.
SECRET_KEY = os.environ.get("ASAD_SECRET", "asad-dev-secret-change-me-in-production")
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 ngày

# Tài khoản admin khởi tạo lần đầu (đổi mật khẩu sau khi đăng nhập).
ADMIN_EMAIL = os.environ.get("ASAD_ADMIN_EMAIL", "admin@asad.local")
ADMIN_PASSWORD = os.environ.get("ASAD_ADMIN_PASSWORD", "admin123")

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
