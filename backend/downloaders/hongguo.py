from __future__ import annotations

from .base import BaseDownloader, DownloadContext, DownloadResult, ProgressCallback, registry


@registry.register("hongguo")
class HongguoDownloader(BaseDownloader):
    """Placeholder cho Hongguo (红果短剧).

    Khi có API, bổ sung vào phương thức ``download()`` và đổi ``enabled = True``.
    """

    name = "Hongguo (红果短剧)"
    description = "Chưa cấu hình API. Bổ sung logic gọi API riêng khi bạn có key."
    enabled = False

    @classmethod
    def matches(cls, url: str) -> bool:
        host_markers = ("hongguo", "hgdj", "hg-duanju")
        return any(marker in url for marker in host_markers)

    async def download(
        self,
        ctx: DownloadContext,
        on_progress: ProgressCallback,
    ) -> DownloadResult:
        raise NotImplementedError(
            "Hongguo downloader chưa được cấu hình. "
            "Hãy điền API key / logic resolve vào backend/downloaders/hongguo.py."
        )
