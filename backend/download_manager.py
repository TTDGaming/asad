from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .config import VIDEO_DIR
from .database import SessionLocal
from .downloaders import DownloadContext, registry
from .models import Download, DownloadStatus

logger = logging.getLogger(__name__)


class DownloadManager:
    """Background worker that processes download jobs sequentially.

    Multiple jobs can be queued, but to keep things simple and avoid
    saturating the connection, only one job runs at a time. Progress is
    persisted to the DB so any client (Windows / iPhone) can poll for it.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._current_job: int | None = None

    def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    def enqueue(self, download_id: int) -> None:
        self._queue.put_nowait(download_id)

    async def _worker(self) -> None:
        while True:
            download_id = await self._queue.get()
            self._current_job = download_id
            try:
                await self._run_job(download_id)
            except Exception:  # pragma: no cover
                logger.exception("Download job %s crashed", download_id)
            finally:
                self._current_job = None
                self._queue.task_done()

    async def _run_job(self, download_id: int) -> None:
        db: Session = SessionLocal()
        try:
            job = db.get(Download, download_id)
            if job is None:
                return
            if job.status == DownloadStatus.cancelled:
                return

            provider_cls = registry.resolve(job.url, job.provider)
            if provider_cls is None:
                job.status = DownloadStatus.failed
                job.error_message = "Không tìm thấy downloader phù hợp."
                db.commit()
                return

            if not provider_cls.enabled and provider_cls.key != "generic":
                job.status = DownloadStatus.failed
                job.error_message = (
                    f"Provider '{provider_cls.key}' chưa được cấu hình API. "
                    "Bạn có thể chọn provider 'generic' với direct URL, "
                    "hoặc bổ sung logic ở backend/downloaders/."
                )
                db.commit()
                return

            job.status = DownloadStatus.downloading
            job.provider = provider_cls.key
            job.progress = 0.0
            job.error_message = None
            db.commit()

            async def on_progress(value: float) -> None:
                fresh = SessionLocal()
                try:
                    row = fresh.get(Download, download_id)
                    if row is None:
                        return
                    row.progress = float(value)
                    fresh.commit()
                finally:
                    fresh.close()

            ctx = DownloadContext(
                url=job.url,
                output_dir=Path(VIDEO_DIR),
                filename_hint=f"project{job.project_id}",
            )
            downloader = provider_cls()

            try:
                result = await downloader.download(ctx, on_progress)
            except Exception as exc:
                logger.exception("Download %s failed", download_id)
                fresh = SessionLocal()
                try:
                    row = fresh.get(Download, download_id)
                    if row is not None:
                        row.status = DownloadStatus.failed
                        row.error_message = str(exc)
                        fresh.commit()
                finally:
                    fresh.close()
                return

            fresh = SessionLocal()
            try:
                row = fresh.get(Download, download_id)
                if row is not None:
                    row.status = DownloadStatus.completed
                    row.progress = 1.0
                    row.file_path = str(result.file_path.relative_to(VIDEO_DIR.parent.parent)) \
                        if VIDEO_DIR.parent.parent in result.file_path.parents \
                        else str(result.file_path)
                    row.file_size = result.file_size
                    row.completed_at = datetime.utcnow()
                    fresh.commit()
            finally:
                fresh.close()
        finally:
            db.close()


manager = DownloadManager()
