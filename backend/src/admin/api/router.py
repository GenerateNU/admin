from fastapi import APIRouter

from admin.api.v1 import (
    access_requests,
    audit,
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

root_router = APIRouter()
root_router.include_router(health.router)
