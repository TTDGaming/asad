from __future__ import annotations

from .base import BaseDownloader, DownloadContext, DownloadResult, ProgressCallback, registry


@registry.register("douyin")
class DouyinDownloader(BaseDownloader):
    """Placeholder cho Douyin (抖音).

    Khi bạn có API / key thực, hãy:
      1. Viết hàm resolve() nhận URL share của Douyin và trả về direct media URL.
      2. Dùng lại GenericHttpDownloader ở bước tải, hoặc tự stream bằng httpx.
      3. Bật ``enabled = True`` và cập nhật ``matches()`` nếu muốn auto-detect.
    """

    name = "Douyin (抖音)"
    description = "Chưa cấu hình API. Thêm logic gọi API riêng rồi stream file về storage/videos."
    enabled = False

    @classmethod
    def matches(cls, url: str) -> bool:
        host_markers = ("douyin.com", "iesdouyin.com", "v.douyin.com")
        return any(marker in url for marker in host_markers)

    async def download(
        self,
        ctx: DownloadContext,
        on_progress: ProgressCallback,
    ) -> DownloadResult:
        raise NotImplementedError(
            "Douyin downloader chưa được cấu hình. "
            "Hãy điền API key / logic resolve vào backend/downloaders/douyin.py."
        )
