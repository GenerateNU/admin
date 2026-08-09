import uuid
from datetime import datetime
from typing import Any

from admin.domain.enums import AuditAction
from admin.schemas.base import ReadDTO


class AuditEntry(ReadDTO):
    actor_id: uuid.UUID | None = None
    actor_email: str | None = None
    action: AuditAction
    resource_type: str
    resource_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class AuditLogRead(AuditEntry):
    id: uuid.UUID
    created_at: datetime
