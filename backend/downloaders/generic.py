from __future__ import annotations

import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import httpx

from .base import BaseDownloader, DownloadContext, DownloadResult, ProgressCallback, registry


_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    name = _SAFE_CHARS.sub("_", name).strip("_")
    return name or "video"


@registry.register("generic")
class GenericHttpDownloader(BaseDownloader):
    """Stream any direct HTTP(S) video URL to disk."""

    name = "Generic HTTP"
    description = "Tải trực tiếp từ URL HTTP/HTTPS (mp4, m3u8 single, v.v.)."

    @classmethod
    def matches(cls, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    async def download(
        self,
        ctx: DownloadContext,
        on_progress: ProgressCallback,
    ) -> DownloadResult:
        parsed = urlparse(ctx.url)
        path_name = Path(parsed.path).name or "video.mp4"
        if "." not in path_name:
            path_name += ".mp4"
        base_name = ctx.filename_hint or path_name
        filename = f"{uuid.uuid4().hex[:8]}_{_safe_filename(base_name)}"
        out_path = ctx.output_dir / filename

        async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
            async with client.stream("GET", ctx.url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length") or 0)
                downloaded = 0

                async with aiofiles.open(out_path, "wb") as fh:
                    async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        await fh.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            await on_progress(min(downloaded / total, 0.999))

        size = out_path.stat().st_size
        await on_progress(1.0)
        return DownloadResult(file_path=out_path, file_size=size)
