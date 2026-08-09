import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from admin.api.dependencies import AuthContext, InvitationServiceDep, require
from admin.domain.permissions import Permission
from admin.schemas.invitation import InvitationCreate, InvitationCreated, InvitationRead

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("", response_model=list[InvitationRead])
async def list_invitations(
    service: InvitationServiceDep,
    _: Annotated[AuthContext, Depends(require(Permission.MEMBERS_INVITE))],
) -> list[InvitationRead]:
    return await service.list_open()


@router.post("", response_model=InvitationCreated, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: InvitationCreate,
    service: InvitationServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.MEMBERS_INVITE))],
) -> InvitationCreated:
    return await service.create(
        actor=context.user, actor_permissions=context.permissions, payload=payload
    )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    service: InvitationServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.MEMBERS_INVITE))],
) -> None:
    await service.revoke(actor=context.user, invitation_id=invitation_id)
