from generate_admin.core.errors import LastOwnerError, PrivilegeEscalationError
from generate_admin.domain.access import PermissionSet
from generate_admin.domain.permissions import Permission, SystemRole
from generate_admin.repositories.user import UserRepository
from generate_admin.schemas.role import RoleRead


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
