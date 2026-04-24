from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIR
from .database import init_db
from .download_manager import manager
from .routers import downloads, projects, translations


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    manager.start()
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(title="Asad - Video Translation & Download Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(translations.router)
app.include_router(downloads.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
