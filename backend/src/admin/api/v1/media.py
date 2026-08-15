import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from admin.api.dependencies import CurrentUser, MediaServiceDep
from admin.schemas.media import (
    MediaPresetRead,
    MediaRead,
    MediaUploadRequest,
    MediaUploadTicket,
)

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/presets", response_model=list[MediaPresetRead])
async def list_presets(service: MediaServiceDep, _: CurrentUser) -> list[MediaPresetRead]:
    return service.presets()


@router.post(
    "/upload-tickets",
    response_model=list[MediaUploadTicket],
    status_code=status.HTTP_201_CREATED,
)
async def create_upload_tickets(
    payload: MediaUploadRequest, service: MediaServiceDep, context: CurrentUser
) -> list[MediaUploadTicket]:
    return await service.create_upload_tickets(actor=context.user, payload=payload)


@router.get("", response_model=list[MediaRead])
async def list_media(
    service: MediaServiceDep,
    context: CurrentUser,
    ids: Annotated[list[uuid.UUID], Query()],
) -> list[MediaRead]:
    return await service.get_files(
        actor=context.user, actor_permissions=context.permissions, media_ids=ids
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    service: MediaServiceDep,
    context: CurrentUser,
    ids: Annotated[list[uuid.UUID], Query()],
) -> None:
    await service.delete_files(
        actor=context.user, actor_permissions=context.permissions, media_ids=ids
    )


@router.post("/{media_id}/complete", response_model=MediaRead)
async def complete_upload(
    media_id: uuid.UUID, service: MediaServiceDep, context: CurrentUser
) -> MediaRead:
    return await service.complete_upload(actor=context.user, media_id=media_id)


@router.get("/{media_id}", response_model=MediaRead)
async def get_media(
    media_id: uuid.UUID, service: MediaServiceDep, context: CurrentUser
) -> MediaRead:
    return await service.get_file(
        actor=context.user, actor_permissions=context.permissions, media_id=media_id
    )


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_single_media(
    media_id: uuid.UUID, service: MediaServiceDep, context: CurrentUser
) -> None:
    await service.delete_file(
        actor=context.user, actor_permissions=context.permissions, media_id=media_id
    )
