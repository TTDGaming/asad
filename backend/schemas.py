from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import DownloadStatus, TranslationStatus


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    source_url: str | None = None
    provider: str | None = None
    source_language: str | None = None
    target_language: str | None = None
    cover_url: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    source_url: str | None = None
    provider: str | None = None
    source_language: str | None = None
    target_language: str | None = None
    cover_url: str | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class DownloadCreate(BaseModel):
    project_id: int
    url: str
    provider: str | None = None


class DownloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    url: str
    provider: str
    status: DownloadStatus
    progress: float
    file_path: str | None
    file_size: int | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class TranslationBase(BaseModel):
    start_time: float | None = None
    end_time: float | None = None
    source_text: str = ""
    translated_text: str = ""
    note: str | None = None
    status: TranslationStatus = TranslationStatus.draft
    order_index: int = 0


class TranslationCreate(TranslationBase):
    project_id: int


class TranslationUpdate(BaseModel):
    start_time: float | None = None
    end_time: float | None = None
    source_text: str | None = None
    translated_text: str | None = None
    note: str | None = None
    status: TranslationStatus | None = None
    order_index: int | None = None


class TranslationOut(TranslationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class ProviderInfo(BaseModel):
    key: str
    name: str
    enabled: bool
    description: str | None = None
