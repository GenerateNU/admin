import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from admin.api.dependencies import AuthContext, BranchServiceDep, require
from admin.domain.permissions import Permission
from admin.schemas.branch import (
    BranchDraftCreate,
    BranchDraftRead,
    BranchDraftReorder,
    BranchDraftUpdate,
    BranchPublishStatus,
    BranchRead,
)

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("/drafts", response_model=list[BranchDraftRead])
async def list_drafts(
    service: BranchServiceDep,
    _: Annotated[AuthContext, Depends(require(Permission.BRANCHES_READ))],
) -> list[BranchDraftRead]:
    return await service.list_drafts()


@router.post("/drafts", response_model=BranchDraftRead, status_code=status.HTTP_201_CREATED)
async def create_draft(
    payload: BranchDraftCreate,
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_MANAGE))],
) -> BranchDraftRead:
    return await service.create_draft(actor=context.user, payload=payload)


@router.patch("/drafts/{branch_id}", response_model=BranchDraftRead)
async def update_draft(
    branch_id: uuid.UUID,
    payload: BranchDraftUpdate,
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_MANAGE))],
) -> BranchDraftRead:
    return await service.update_draft(actor=context.user, branch_id=branch_id, payload=payload)


@router.delete("/drafts/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    branch_id: uuid.UUID,
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_MANAGE))],
) -> None:
    await service.delete_draft(actor=context.user, branch_id=branch_id)


@router.post("/drafts/reorder", response_model=list[BranchDraftRead])
async def reorder_drafts(
    payload: BranchDraftReorder,
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_MANAGE))],
) -> list[BranchDraftRead]:
    return await service.reorder_drafts(actor=context.user, ordered_ids=payload.ids)


@router.get("/status", response_model=BranchPublishStatus)
async def publish_status(
    service: BranchServiceDep,
    _: Annotated[AuthContext, Depends(require(Permission.BRANCHES_READ))],
) -> BranchPublishStatus:
    return await service.publish_status()


@router.post("/publish", response_model=list[BranchRead])
async def publish(
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_PUBLISH))],
) -> list[BranchRead]:
    return await service.publish(actor=context.user)


@router.post("/discard", response_model=list[BranchDraftRead])
async def discard(
    service: BranchServiceDep,
    context: Annotated[AuthContext, Depends(require(Permission.BRANCHES_PUBLISH))],
) -> list[BranchDraftRead]:
    return await service.discard_drafts(actor=context.user)
