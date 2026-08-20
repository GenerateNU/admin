from fastapi import APIRouter

from admin.api.public.v1 import branches as public_branches
from admin.api.v1 import (
    access_requests,
    audit,
    branches,
    health,
    invitations,
    media,
    members,
    roles,
    session,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(session.router)
api_router.include_router(members.router)
api_router.include_router(invitations.router)
api_router.include_router(access_requests.router)
api_router.include_router(roles.router)
api_router.include_router(media.router)
api_router.include_router(audit.router)
api_router.include_router(branches.router)

public_router = APIRouter(prefix="/public/v1")
public_router.include_router(public_branches.router)

root_router = APIRouter()
root_router.include_router(health.router)
