from fastapi import APIRouter, status

from admin.api.dependencies import (
    AccessRequestServiceDep,
    CurrentIdentity,
    CurrentSession,
)
from admin.schemas.access_request import AccessRequestCreate, AccessRequestRead
from admin.schemas.session import Session

router = APIRouter(tags=["session"])


@router.get("/session", response_model=Session)
async def read_session(session: CurrentSession) -> Session:
    return session


@router.post(
    "/session/access-request",
    response_model=AccessRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def request_access(
    identity: CurrentIdentity,
    payload: AccessRequestCreate,
    service: AccessRequestServiceDep,
) -> AccessRequestRead:
    return await service.create(identity=identity, payload=payload)
