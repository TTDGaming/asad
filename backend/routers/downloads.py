from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import VIDEO_DIR
from ..database import get_db
from ..download_manager import manager
from ..downloaders import registry
from ..models import Download, DownloadStatus, Project
from ..schemas import DownloadCreate, DownloadOut, ProviderInfo

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


@router.get("/providers", response_model=list[ProviderInfo])
def list_providers():
    items = []
    for cls in registry.all():
        items.append(
            ProviderInfo(
                key=cls.key,
                name=cls.name or cls.key,
                enabled=cls.enabled,
                description=cls.description,
            )
        )
    return items


@router.get("", response_model=list[DownloadOut])
def list_downloads(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Download)
    if project_id is not None:
        q = q.filter(Download.project_id == project_id)
    return q.order_by(Download.created_at.desc()).all()


@router.post("", response_model=DownloadOut, status_code=201)
def create_download(payload: DownloadCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")

    provider_cls = registry.resolve(payload.url, payload.provider)
    if provider_cls is None:
        raise HTTPException(400, "Không tìm được downloader phù hợp với URL này.")

    row = Download(
        project_id=payload.project_id,
        url=payload.url,
        provider=provider_cls.key,
        status=DownloadStatus.pending,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    manager.enqueue(row.id)
    return row


@router.get("/{download_id}", response_model=DownloadOut)
def get_download(download_id: int, db: Session = Depends(get_db)):
    row = db.get(Download, download_id)
    if row is None:
        raise HTTPException(404, "Download not found")
    return row


@router.post("/{download_id}/cancel", response_model=DownloadOut)
def cancel_download(download_id: int, db: Session = Depends(get_db)):
    row = db.get(Download, download_id)
    if row is None:
        raise HTTPException(404, "Download not found")
    if row.status in (DownloadStatus.pending, DownloadStatus.downloading):
        row.status = DownloadStatus.cancelled
        db.commit()
        db.refresh(row)
    return row


@router.post("/{download_id}/retry", response_model=DownloadOut)
def retry_download(download_id: int, db: Session = Depends(get_db)):
    row = db.get(Download, download_id)
    if row is None:
        raise HTTPException(404, "Download not found")
    row.status = DownloadStatus.pending
    row.progress = 0.0
    row.error_message = None
    row.file_path = None
    row.file_size = None
    row.completed_at = None
    db.commit()
    db.refresh(row)
    manager.enqueue(row.id)
    return row


@router.delete("/{download_id}", status_code=204)
def delete_download(download_id: int, db: Session = Depends(get_db)):
    row = db.get(Download, download_id)
    if row is None:
        raise HTTPException(404, "Download not found")
    db.delete(row)
    db.commit()
    return None


@router.get("/{download_id}/file")
def download_file(download_id: int, db: Session = Depends(get_db)):
    """Trả file video về client để lưu trực tiếp (Windows / iPhone)."""
    row = db.get(Download, download_id)
    if row is None or not row.file_path:
        raise HTTPException(404, "File not available")
    from pathlib import Path

    path = Path(row.file_path)
    if not path.is_absolute():
        path = VIDEO_DIR.parent.parent / path
    if not path.exists():
        raise HTTPException(404, "File missing on disk")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
    )
