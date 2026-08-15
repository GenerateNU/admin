import uuid

from admin.repositories.base import Repository, required_row
from admin.schemas.media import MediaCreate, MediaRecord, MediaUploadingStatus

MEDIA_SELECT = """
SELECT m.id,
       m.owner_id,
       m.s3_key,
       m.original_filename,
       m.mime_type,
       m.size_bytes,
       m.purpose,
       m.visibility,
       m.status,
       m.created_at,
       m.updated_at
FROM media m
"""


class MediaRepository(Repository):
    async def insert(self, payload: MediaCreate) -> MediaRecord:
        row = required_row(
            await self.connection.fetchrow(
                """
                INSERT INTO media (
                    owner_id, s3_key, original_filename, mime_type,
                    size_bytes, purpose, visibility, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, owner_id, s3_key, original_filename, mime_type,
                          size_bytes, purpose, visibility, status, created_at, updated_at
                """,
                payload.owner_id,
                payload.s3_key,
                payload.original_filename,
                payload.mime_type,
                payload.size_bytes,
                payload.purpose.value,
                payload.visibility.value,
                payload.status.value,
            )
        )
        return MediaRecord.from_row(row)

    async def update_status(
        self,
        media_id: uuid.UUID,
        status: MediaUploadingStatus,
        *,
        size_bytes: int | None = None,
    ) -> MediaRecord | None:
        row = await self.connection.fetchrow(
            """
            UPDATE media
            SET status = $2,
                size_bytes = COALESCE($3, size_bytes),
                updated_at = now()
            WHERE id = $1
            RETURNING id, owner_id, s3_key, original_filename, mime_type,
                      size_bytes, purpose, visibility, status, created_at, updated_at
            """,
            media_id,
            status.value,
            size_bytes,
        )
        return MediaRecord.from_optional_row(row)

    async def get_by_id(self, media_id: uuid.UUID) -> MediaRecord | None:
        row = await self.connection.fetchrow(f"{MEDIA_SELECT} WHERE m.id = $1", media_id)
        return MediaRecord.from_optional_row(row)

    async def get_by_ids(self, media_ids: list[uuid.UUID]) -> list[MediaRecord]:
        if not media_ids:
            return []

        rows = await self.connection.fetch(
            f"{MEDIA_SELECT} WHERE m.id = ANY($1) ORDER BY m.created_at DESC", media_ids
        )
        return MediaRecord.from_rows(rows)

    async def delete_by_id(self, media_id: uuid.UUID) -> MediaRecord | None:
        row = await self.connection.fetchrow(
            """
            DELETE FROM media
            WHERE id = $1
            RETURNING id, owner_id, s3_key, original_filename, mime_type,
                      size_bytes, purpose, visibility, status, created_at, updated_at
            """,
            media_id,
        )
        return MediaRecord.from_optional_row(row)

    async def delete_by_ids(self, media_ids: list[uuid.UUID]) -> list[MediaRecord]:
        if not media_ids:
            return []

        rows = await self.connection.fetch(
            """
            DELETE FROM media
            WHERE id = ANY($1)
            RETURNING id, owner_id, s3_key, original_filename, mime_type,
                      size_bytes, purpose, visibility, status, created_at, updated_at
            """,
            media_ids,
        )
        return MediaRecord.from_rows(rows)

    async def variant_keys_for(self, media_ids: list[uuid.UUID]) -> list[str]:
        if not media_ids:
            return []

        rows = await self.connection.fetch(
            "SELECT s3_key FROM media_variants WHERE media_id = ANY($1)", media_ids
        )
        return [row["s3_key"] for row in rows]
