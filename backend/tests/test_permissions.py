import uuid

import pytest

from admin.core.errors import PrivilegeEscalationError
from admin.domain.access import PermissionSet
from admin.domain.permissions import (
    ROLE_DEFINITIONS_BY_KEY,
    Permission,
    SystemRole,
)
from admin.schemas.role import RoleRead
from admin.services.guards import ensure_can_delegate


def role_for(key: SystemRole) -> RoleRead:
    definition = ROLE_DEFINITIONS_BY_KEY[key]
    return RoleRead(
        id=uuid.uuid4(),
        key=definition.key.value,
        name=definition.name,
        is_system=True,
        permissions=sorted(permission.value for permission in definition.permissions),
    )


def permissions_for(key: SystemRole) -> PermissionSet:
    definition = ROLE_DEFINITIONS_BY_KEY[key]
    return PermissionSet.from_keys([permission.value for permission in definition.permissions])


def test_owner_holds_every_permission() -> None:
    owner = permissions_for(SystemRole.OWNER)

    assert owner.allows_all(set(Permission))
    assert not owner.is_empty


def test_admin_cannot_hand_out_roles() -> None:
    admin = permissions_for(SystemRole.ADMIN)

    assert admin.allows(Permission.MEMBERS_INVITE)
    assert admin.allows(Permission.ACCESS_REQUESTS_REVIEW)
    assert not admin.allows(Permission.ROLES_GRANT)
    assert not admin.allows(Permission.ROLES_REVOKE)


def test_empty_permission_set_allows_nothing() -> None:
    nobody = PermissionSet.from_keys([])

    assert nobody.is_empty
    assert not nobody.allows(Permission.MEMBERS_READ)


def test_admin_may_not_delegate_owner() -> None:
    with pytest.raises(PrivilegeEscalationError) as error:
        ensure_can_delegate(permissions_for(SystemRole.ADMIN), role_for(SystemRole.OWNER))

    assert error.value.details["missing"] == [
        Permission.ROLES_GRANT.value,
        Permission.ROLES_REVOKE.value,
    ]


def test_owner_may_delegate_admin() -> None:
    ensure_can_delegate(permissions_for(SystemRole.OWNER), role_for(SystemRole.ADMIN))
