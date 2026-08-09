import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from generate_admin.domain.enums import InvitationStatus
from generate_admin.schemas.base import ReadDTO, RequestDTO
from generate_admin.schemas.role import RoleSummary


class InvitationCreate(RequestDTO):
    email: EmailStr
    role_id: uuid.UUID
    expires_in_hours: int | None = Field(default=None, ge=1, le=8760)


class InvitationRead(ReadDTO):
    id: uuid.UUID
    email: EmailStr
    role: RoleSummary
    status: InvitationStatus
    invited_by: uuid.UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationCreated(ReadDTO):
    invitation: InvitationRead
    token: str
