from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DownloadStatus(str, PyEnum):
    pending = "pending"
    downloading = "downloading"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TranslationStatus(str, PyEnum):
    draft = "draft"
    in_progress = "in_progress"
    reviewing = "reviewing"
    completed = "completed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(64))
    source_language: Mapped[str | None] = mapped_column(String(16))
    target_language: Mapped[str | None] = mapped_column(String(16))
    cover_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    downloads: Mapped[list["Download"]] = relationship(
        "Download", back_populates="project", cascade="all, delete-orphan"
    )
    translations: Mapped[list["Translation"]] = relationship(
        "Translation", back_populates="project", cascade="all, delete-orphan"
    )


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.pending, nullable=False
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    file_path: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    project: Mapped[Project] = relationship("Project", back_populates="downloads")


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[float | None] = mapped_column(Float)
    end_time: Mapped[float | None] = mapped_column(Float)
    source_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    translated_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TranslationStatus] = mapped_column(
        Enum(TranslationStatus), default=TranslationStatus.draft, nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped[Project] = relationship("Project", back_populates="translations")
