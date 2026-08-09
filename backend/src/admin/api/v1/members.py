import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from admin.api.dependencies import AuthContext, MemberServiceDep, require
from admin.domain.permissions import Permission
from admin.schemas.role import RoleGrantRequest
from admin.schemas.user import UserRead

router = APIRouter(prefix="/members", tags=["members"])


@router.get("/{user_id}", response_model=UserRead)
async def get_member(
    user_id: uuid.UUID,
    service: MemberServiceDep,
    _: Annotated[AuthContext, Depends(require(Permission.MEMBERS_READ))],
) -> UserRead:
    return await service.get_member(user_id)


@router.post("/{user_id}/roles", response_model=UserRead)
async def grant_role(
    user_id: uuid.UUID,
    payload: RoleGrantRequest,
    service: MemberServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.ROLES_GRANT))],
) -> UserRead:
    return await service.grant_role(
        actor=context.user,
        actor_permissions=context.permissions,
        user_id=user_id,
        payload=payload,
    )


@router.delete("/roles/{assignment_id}", response_model=UserRead)
async def revoke_role(
    assignment_id: uuid.UUID,
    service: MemberServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.ROLES_REVOKE))],
) -> UserRead:
    return await service.revoke_role(actor=context.user, assignment_id=assignment_id)
