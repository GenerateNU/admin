import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from admin.api.dependencies import AuditEntries, AuthContext, require
from admin.domain.permissions import Permission
from admin.schemas.audit import AuditLogRead
from admin.schemas.base import CursorPage, CursorParams

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=CursorPage[AuditLogRead])
async def list_audit_entries(
    entries: AuditEntries,
    params: Annotated[CursorParams, Depends()],
    _: Annotated[AuthContext, Depends(require(Permission.AUDIT_READ))],
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> CursorPage[AuditLogRead]:
    rows = await entries.list_entries(
        params,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return CursorPage[AuditLogRead].build(rows, params, lambda item: [item.created_at, item.id])
