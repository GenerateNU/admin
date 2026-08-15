import asyncio
import uuid

from admin.core.audit import AuditLog
from admin.core.errors import NotFoundError, ValidationError
from admin.core.logging import get_logger
from admin.core.storage import MediaUrl, S3Storage, build_object_key
from admin.domain.access import PermissionSet
from admin.domain.enums import AuditAction
from admin.domain.media import PRESETS, preset_for
from admin.repositories.media import MediaRepository
from admin.schemas.audit import AuditEntry
from admin.schemas.media import (
    MediaCreate,
    MediaPresetRead,
    MediaRead,
    MediaRecord,
    MediaUploadingStatus,
    MediaUploadRequest,
    MediaUploadTicket,
)
from admin.schemas.user import UserRead
from admin.services.guards import ensure_can_delete, ensure_can_read, ensure_owns

logger = get_logger(__name__)

RESOURCE_TYPE = "media"


class MediaService:
    def __init__(self, *, media: MediaRepository, storage: S3Storage, audit: AuditLog) -> None:
        self._media = media
        self._storage = storage
        self._audit = audit

    def presets(self) -> list[MediaPresetRead]:
        return [
            MediaPresetRead(
                purpose=purpose,
                max_edge=preset.max_edge,
                max_bytes=preset.max_bytes,
                mime_types=sorted(preset.mime_types),
            )
            for purpose, preset in PRESETS.items()
        ]

    async def create_upload_tickets(
        self, *, actor: UserRead, payload: MediaUploadRequest
    ) -> list[MediaUploadTicket]:
        preset = preset_for(payload.purpose)
        max_bytes = min(preset.max_bytes, self._storage.max_upload_bytes)

        for item in payload.files:
            if item.mime_type not in preset.mime_types:
                raise ValidationError(
                    f"{item.mime_type} is not accepted for {payload.purpose.value}",
                    details={"allowed": sorted(preset.mime_types)},
                )
            if item.size_bytes > max_bytes:
                raise ValidationError(
                    f"{item.filename} is larger than the {max_bytes} byte limit",
                    details={"max_bytes": max_bytes},
                )

        tickets: list[MediaUploadTicket] = []
        for item in payload.files:
            key = build_object_key(visibility=preset.visibility, filename=item.filename)
            ticket = self._storage.create_upload_ticket(
                key=key,
                content_type=item.mime_type,
                visibility=preset.visibility,
                max_bytes=max_bytes,
            )
            record = await self._media.insert(
                MediaCreate(
                    owner_id=actor.id,
                    s3_key=key,
                    original_filename=item.filename,
                    mime_type=item.mime_type,
                    size_bytes=item.size_bytes,
                    purpose=payload.purpose,
                    visibility=preset.visibility,
                    status=MediaUploadingStatus.UPLOADING,
                )
            )
            tickets.append(
                MediaUploadTicket(
                    media_id=record.id,
                    url=ticket.url,
                    fields=ticket.fields,
                    s3_key=ticket.key,
                    expires_in=ticket.expires_in,
                )
            )

        return tickets

    async def complete_upload(self, *, actor: UserRead, media_id: uuid.UUID) -> MediaRead:
        record = await self._require(media_id)
        ensure_owns(record, actor=actor)

        metadata = await self._storage.head(record.s3_key)
        if metadata is None:
            await self._media.update_status(media_id, MediaUploadingStatus.FAILED)
            raise ValidationError("the file was never uploaded")

        updated = await self._media.update_status(
            media_id, MediaUploadingStatus.COMPLETED, size_bytes=metadata.size_bytes
        )
        if updated is None:
            raise NotFoundError("media does not exist")

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.MEDIA_UPLOADED,
                resource_type=RESOURCE_TYPE,
                resource_id=str(media_id),
                after={
                    "purpose": updated.purpose.value,
                    "mime_type": updated.mime_type,
                    "size_bytes": updated.size_bytes,
                },
            )
        )

        return await self._to_read(updated)

    async def get_file(
        self, *, actor: UserRead, actor_permissions: PermissionSet, media_id: uuid.UUID
    ) -> MediaRead:
        record = await self._require(media_id)
        ensure_can_read(record, actor=actor, permissions=actor_permissions)
        return await self._to_read(record)

    async def get_files(
        self, *, actor: UserRead, actor_permissions: PermissionSet, media_ids: list[uuid.UUID]
    ) -> list[MediaRead]:
        records = await self._media.get_by_ids(media_ids)
        for record in records:
            ensure_can_read(record, actor=actor, permissions=actor_permissions)

        urls = await asyncio.gather(*(self._url_for(record) for record in records))
        return [self._build_read(record, url) for record, url in zip(records, urls, strict=True)]

    async def delete_file(
        self, *, actor: UserRead, actor_permissions: PermissionSet, media_id: uuid.UUID
    ) -> None:
        await self.delete_files(
            actor=actor, actor_permissions=actor_permissions, media_ids=[media_id]
        )

    async def delete_files(
        self, *, actor: UserRead, actor_permissions: PermissionSet, media_ids: list[uuid.UUID]
    ) -> None:
        if not media_ids:
            return

        records = await self._media.get_by_ids(media_ids)
        if len(records) != len(set(media_ids)):
            raise NotFoundError("media does not exist")

        for record in records:
            ensure_can_delete(record, actor=actor, permissions=actor_permissions)

        variant_keys = await self._media.variant_keys_for(media_ids)
        deleted = await self._media.delete_by_ids(media_ids)

        self._audit.add(
            *(
                AuditEntry(
                    actor_id=actor.id,
                    actor_email=actor.email,
                    action=AuditAction.MEDIA_DELETED,
                    resource_type=RESOURCE_TYPE,
                    resource_id=str(record.id),
                    before={
                        "owner_id": str(record.owner_id),
                        "s3_key": record.s3_key,
                        "purpose": record.purpose.value,
                    },
                )
                for record in deleted
            )
        )

        keys = [record.s3_key for record in deleted] + variant_keys
        try:
            await self._storage.delete_many(keys)
        except Exception:
            logger.exception("media_s3_delete_failed", keys=keys)

    def public_url(self, s3_key: str) -> str:
        return self._storage.public_url(s3_key)

    async def _require(self, media_id: uuid.UUID) -> MediaRecord:
        record = await self._media.get_by_id(media_id)
        if record is None:
            raise NotFoundError("media does not exist")
        return record

    async def _url_for(self, record: MediaRecord) -> MediaUrl:
        return await self._storage.url_for(key=record.s3_key, visibility=record.visibility)

    async def _to_read(self, record: MediaRecord) -> MediaRead:
        return self._build_read(record, await self._url_for(record))

    def _build_read(self, record: MediaRecord, url: MediaUrl) -> MediaRead:
        return MediaRead(
            id=record.id,
            url=url.url,
            url_expires_at=url.expires_at,
            original_filename=record.original_filename,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            purpose=record.purpose,
            visibility=record.visibility,
            status=record.status,
            created_at=record.created_at,
        )
