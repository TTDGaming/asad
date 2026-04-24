from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
VIDEO_DIR = STORAGE_DIR / "videos"
SUBTITLE_DIR = STORAGE_DIR / "subtitles"
DB_PATH = BASE_DIR / "storage" / "app.db"
FRONTEND_DIR = BASE_DIR / "frontend"

DATABASE_URL = f"sqlite:///{DB_PATH}"

for directory in (STORAGE_DIR, VIDEO_DIR, SUBTITLE_DIR):
    directory.mkdir(parents=True, exist_ok=True)
