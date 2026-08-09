from typing import Annotated

from fastapi import APIRouter, Depends

from admin.api.dependencies import AuthContext, Roles, require
from admin.domain.permissions import Permission
from admin.schemas.role import PermissionRead, RoleRead

router = APIRouter(tags=["roles"])


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    roles: Roles,
    _: Annotated[AuthContext, Depends(require(Permission.ROLES_READ))],
) -> list[RoleRead]:
    return await roles.list_roles()


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    roles: Roles,
    _: Annotated[AuthContext, Depends(require(Permission.ROLES_READ))],
) -> list[PermissionRead]:
    return await roles.list_permissions()
