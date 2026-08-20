from fastapi import APIRouter

from admin.api.dependencies import BranchServiceDep
from admin.schemas.branch import BranchRead

router = APIRouter(prefix="/branches", tags=["public"])


@router.get("", response_model=list[BranchRead])
async def list_public_branches(service: BranchServiceDep) -> list[BranchRead]:
    return await service.list_published()
