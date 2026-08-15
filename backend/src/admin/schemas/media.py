import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import Field

from admin.core.storage import MediaVisibility
from admin.domain.enums import MediaPurpose
from admin.schemas.base import ReadDTO, RequestDTO


class MediaUploadingStatus(StrEnum):
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaCreate(RequestDTO):
    owner_id: uuid.UUID
    s3_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    purpose: MediaPurpose
    visibility: MediaVisibility
    status: MediaUploadingStatus


class MediaUpdate(RequestDTO):
    id: uuid.UUID
    s3_key: str
    owner_id: uuid.UUID
    status: MediaUploadingStatus


class MediaRecord(ReadDTO):
    id: uuid.UUID
    owner_id: uuid.UUID
    s3_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    purpose: MediaPurpose
    visibility: MediaVisibility
    status: MediaUploadingStatus
    created_at: datetime
    updated_at: datetime


class MediaRead(ReadDTO):
    id: uuid.UUID
    url: str
    url_expires_at: datetime | None = None
    original_filename: str
    mime_type: str
    size_bytes: int
    purpose: MediaPurpose
    visibility: MediaVisibility
    status: MediaUploadingStatus
    created_at: datetime


class MediaUploadItem(RequestDTO):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str
    size_bytes: int = Field(gt=0)


class MediaUploadRequest(RequestDTO):
    purpose: MediaPurpose
    files: list[MediaUploadItem] = Field(min_length=1, max_length=20)


class MediaPresetRead(ReadDTO):
    purpose: MediaPurpose
    max_edge: int
    max_bytes: int
    mime_types: list[str]


class MediaUploadTicket(ReadDTO):
    media_id: uuid.UUID
    url: str
    fields: dict[str, str]
    s3_key: str
    expires_in: int
