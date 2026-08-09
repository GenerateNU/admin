import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from admin.domain.enums import AccessRequestStatus
from admin.schemas.base import ReadDTO, RequestDTO


class AccessRequestCreate(RequestDTO):
    message: str | None = Field(default=None, max_length=1000)


class AccessRequestApproval(RequestDTO):
    role_id: uuid.UUID
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)


class AccessRequestDenial(RequestDTO):
    note: str | None = Field(default=None, max_length=1000)


class AccessRequestRead(ReadDTO):
    id: uuid.UUID
    email: EmailStr
    entra_object_id: uuid.UUID
    name: str
    message: str | None
    status: AccessRequestStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    decision_note: str | None
    created_at: datetime
