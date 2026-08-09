import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from admin.api.dependencies import AccessRequestServiceDep, AuthContext, require
from admin.domain.permissions import Permission
from admin.schemas.access_request import (
    AccessRequestApproval,
    AccessRequestDenial,
    AccessRequestRead,
)

router = APIRouter(prefix="/access-requests", tags=["access requests"])


@router.get("", response_model=list[AccessRequestRead])
async def list_pending_requests(
    service: AccessRequestServiceDep,
    _: Annotated[AuthContext, Depends(require(Permission.ACCESS_REQUESTS_READ))],
) -> list[AccessRequestRead]:
    return await service.list_pending()


@router.post("/{request_id}/approve", response_model=AccessRequestRead)
async def approve_request(
    request_id: uuid.UUID,
    payload: AccessRequestApproval,
    service: AccessRequestServiceDep,
    context: Annotated[
        AuthContext,
        Depends(require(Permission.ACCESS_REQUESTS_REVIEW, Permission.ROLES_GRANT)),
    ],
) -> AccessRequestRead:
    return await service.approve(
        actor=context.user,
        actor_permissions=context.permissions,
        request_id=request_id,
        payload=payload,
    )


@router.post("/{request_id}/deny", response_model=AccessRequestRead)
async def deny_request(
    request_id: uuid.UUID,
    payload: AccessRequestDenial,
    service: AccessRequestServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.ACCESS_REQUESTS_REVIEW))],
) -> AccessRequestRead:
    return await service.deny(actor=context.user, request_id=request_id, payload=payload)
