import uuid
from datetime import datetime

from pydantic import Field

from generate_admin.schemas.base import ReadDTO, RequestDTO


class PermissionRead(ReadDTO):
    key: str
    description: str


class RoleSummary(ReadDTO):
    id: uuid.UUID
    key: str
    name: str


class RoleRead(RoleSummary):
    is_system: bool
    permissions: list[str] = Field(default_factory=list)


class RoleAssignmentRead(ReadDTO):
    id: uuid.UUID
    role: RoleSummary
    granted_at: datetime
    expires_at: datetime | None


class RoleGrantRequest(RequestDTO):
    role_id: uuid.UUID
    expires_at: datetime | None = None
