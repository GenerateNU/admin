from fastapi import APIRouter

from generate_admin.api.v1 import health

api_router = APIRouter(prefix="/api/v1")

root_router = APIRouter()
root_router.include_router(health.router)
