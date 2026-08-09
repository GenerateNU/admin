import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from generate_admin.domain.enums import UserStatus
from generate_admin.schemas.base import ReadDTO
from generate_admin.schemas.role import RoleAssignmentRead


class UserSummary(ReadDTO):
    id: uuid.UUID
    email: EmailStr
    name: str
    status: UserStatus


class UserRead(UserSummary):
    entra_object_id: uuid.UUID
    last_login_at: datetime | None
    created_at: datetime
    role_assignments: list[RoleAssignmentRead] = Field(default_factory=list)
