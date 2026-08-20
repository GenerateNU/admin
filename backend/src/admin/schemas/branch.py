import uuid
from datetime import datetime

from pydantic import Field

from admin.schemas.base import ReadDTO, RequestDTO

COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class BranchDraftCreate(RequestDTO):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon_key: str = Field(min_length=1, max_length=512)
    color: str = Field(pattern=COLOR_PATTERN)
    position: int = Field(default=0, ge=0)


class BranchDraftUpdate(RequestDTO):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon_key: str | None = Field(default=None, min_length=1, max_length=512)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    position: int | None = Field(default=None, ge=0)


class BranchDraftReorder(RequestDTO):
    ids: list[uuid.UUID] = Field(min_length=1)


class BranchDraftRecord(ReadDTO):
    id: uuid.UUID
    name: str
    description: str | None
    icon_key: str
    color: str
    position: int
    created_at: datetime
    updated_at: datetime


class BranchRecord(ReadDTO):
    id: uuid.UUID
    name: str
    description: str | None
    icon_key: str
    color: str
    position: int


class BranchDraftRead(ReadDTO):
    id: uuid.UUID
    name: str
    description: str | None
    icon_key: str
    icon_url: str
    color: str
    position: int
    created_at: datetime
    updated_at: datetime


class BranchRead(ReadDTO):
    id: uuid.UUID
    name: str
    description: str | None
    icon_url: str
    color: str
    position: int


class BranchPublishStatus(ReadDTO):
    is_dirty: bool
    draft_count: int
    published_count: int
    last_published_at: datetime | None
