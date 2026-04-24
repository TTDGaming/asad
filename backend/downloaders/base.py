from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Dict, Type


ProgressCallback = Callable[[float], Awaitable[None]]


@dataclass
class DownloadContext:
    """Runtime data passed to a downloader when a job starts."""

    url: str
    output_dir: Path
    filename_hint: str | None = None


@dataclass
class DownloadResult:
    """What a downloader must return when it finishes successfully."""

    file_path: Path
    file_size: int
    extra: dict | None = None


class BaseDownloader:
    """Base class for all download providers.

    Subclass this and register with ``@registry.register("key")`` to add a new
    provider. At runtime the download manager picks a provider either by the
    explicit ``provider`` field on a :class:`Download` row, or by asking each
    registered provider whether it ``matches(url)``.
    """

    key: str = ""
    name: str = ""
    description: str | None = None
    enabled: bool = True

    @classmethod
    def matches(cls, url: str) -> bool:
        return False

    async def download(
        self,
        ctx: DownloadContext,
        on_progress: ProgressCallback,
    ) -> DownloadResult:
        raise NotImplementedError


class DownloaderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, Type[BaseDownloader]] = {}

    def register(self, key: str):
        def decorator(cls: Type[BaseDownloader]) -> Type[BaseDownloader]:
            cls.key = key
            self._providers[key] = cls
            return cls

        return decorator

    def get(self, key: str) -> Type[BaseDownloader] | None:
        return self._providers.get(key)

    def resolve(self, url: str, provider: str | None = None) -> Type[BaseDownloader] | None:
        if provider:
            cls = self._providers.get(provider)
            if cls is not None:
                return cls
        for cls in self._providers.values():
            if cls.matches(url):
                return cls
        return self._providers.get("generic")

    def all(self) -> list[Type[BaseDownloader]]:
        return list(self._providers.values())


registry = DownloaderRegistry()
