from admin.core.errors import LastOwnerError, PermissionDeniedError, PrivilegeEscalationError
from admin.core.storage import MediaVisibility
from admin.domain.access import PermissionSet
from admin.domain.permissions import Permission, SystemRole
from admin.repositories.user import UserRepository
from admin.schemas.media import MediaRecord
from admin.schemas.role import RoleRead
from admin.schemas.user import UserRead


def ensure_can_delegate(actor: PermissionSet, role: RoleRead) -> None:
    delegated = {Permission(key) for key in role.permissions}
    missing = {permission for permission in delegated if not actor.allows(permission)}
    if missing:
        raise PrivilegeEscalationError(
            "cannot grant permissions you do not hold",
            details={"missing": sorted(permission.value for permission in missing)},
        )


async def ensure_not_last_owner(users: UserRepository, role_key: str) -> None:
    if role_key != SystemRole.OWNER.value:
        return
    if await users.count_active_holders_of_role(SystemRole.OWNER.value) <= 1:
        raise LastOwnerError("the workspace must keep at least one active owner")


def ensure_owns(record: MediaRecord, *, actor: UserRead) -> None:
    if record.owner_id != actor.id:
        raise PermissionDeniedError("you can only complete your own uploads")


def ensure_can_read(record: MediaRecord, *, actor: UserRead, permissions: PermissionSet) -> None:
    if record.visibility is MediaVisibility.PUBLIC:
        return
    if record.owner_id == actor.id:
        return
    if permissions.allows(Permission.MEDIA_READ):
        return
    raise PermissionDeniedError("you do not have access to this file")


def ensure_can_delete(record: MediaRecord, *, actor: UserRead, permissions: PermissionSet) -> None:
    if record.owner_id == actor.id:
        return
    if permissions.allows(Permission.MEDIA_DELETE):
        return
    raise PermissionDeniedError("you can only delete your own files")
