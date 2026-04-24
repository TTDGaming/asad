from .base import BaseDownloader, DownloadContext, DownloadResult, registry
from . import generic, douyin, hongguo  # noqa: F401  - register providers

__all__ = [
    "BaseDownloader",
    "DownloadContext",
    "DownloadResult",
    "registry",
]
