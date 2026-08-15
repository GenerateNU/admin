import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from itertools import batched
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from pydantic import TypeAdapter

from admin.core.cache import Cache, CacheNamespace
from admin.core.config import StorageConfig


class MediaVisibility(StrEnum):
    """Public objects get a stable CDN URL; private ones get signed, expiring URLs."""

    PUBLIC = "public"
    PRIVATE = "private"


PRESIGN_CACHE_RATIO = 0.8
PUBLIC_PREFIX = "public"
PRIVATE_PREFIX = "private"
S3_DELETE_BATCH_SIZE = 1000

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
PRIVATE_CACHE_CONTROL = "private, max-age=0, no-store"


def cache_control_for(visibility: MediaVisibility) -> str:
    return (
        IMMUTABLE_CACHE_CONTROL if visibility is MediaVisibility.PUBLIC else PRIVATE_CACHE_CONTROL
    )


@dataclass(frozen=True, slots=True)
class UploadTicket:
    url: str
    fields: dict[str, str]
    key: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    size_bytes: int
    content_type: str


@dataclass(frozen=True, slots=True)
class MediaUrl:
    url: str
    expires_at: datetime | None = None


MEDIA_URL_ADAPTER = TypeAdapter(MediaUrl)


def build_object_key(*, visibility: MediaVisibility, filename: str) -> str:
    prefix = PUBLIC_PREFIX if visibility is MediaVisibility.PUBLIC else PRIVATE_PREFIX
    stamp = datetime.now(UTC)
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{prefix}/media/{stamp:%Y/%m}/{uuid.uuid4().hex}.{suffix}"


class S3Storage:
    def __init__(self, config: StorageConfig, cache: Cache) -> None:
        self._config = config
        self._cache = cache
        self._client = boto3.client(
            "s3",
            endpoint_url=config.endpoint or None,
            region_name=config.region,
            aws_access_key_id=config.access_key_id.get_secret_value() or None,
            aws_secret_access_key=config.secret_access_key.get_secret_value() or None,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @property
    def max_upload_bytes(self) -> int:
        return self._config.max_upload_bytes

    def create_upload_ticket(
        self,
        *,
        key: str,
        content_type: str,
        visibility: MediaVisibility,
        max_bytes: int | None = None,
    ) -> UploadTicket:
        limit = max_bytes or self._config.max_upload_bytes
        expires_in = self._config.upload_url_ttl_seconds
        cache_control = cache_control_for(visibility)

        presigned: dict[str, Any] = self._client.generate_presigned_post(
            Bucket=self._config.bucket_name,
            Key=key,
            Fields={"Content-Type": content_type, "Cache-Control": cache_control},
            Conditions=[
                {"Content-Type": content_type},
                {"Cache-Control": cache_control},
                ["content-length-range", 1, limit],
            ],
            ExpiresIn=expires_in,
        )
        return UploadTicket(
            url=presigned["url"],
            fields=presigned["fields"],
            key=key,
            expires_in=expires_in,
        )

    def public_url(self, key: str) -> str:
        return self._config.public_url_for(key)

    async def url_for(self, *, key: str, visibility: MediaVisibility) -> MediaUrl:
        if visibility is MediaVisibility.PUBLIC:
            return MediaUrl(url=self.public_url(key))
        return await self.signed_download_url(key)

    async def signed_download_url(self, key: str) -> MediaUrl:
        ttl = self._config.download_url_ttl_seconds

        async def generate() -> MediaUrl:
            url = await asyncio.to_thread(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._config.bucket_name, "Key": key},
                ExpiresIn=ttl,
            )
            return MediaUrl(url=url, expires_at=datetime.now(UTC) + timedelta(seconds=ttl))

        return await self._cache.fetch(
            CacheNamespace.MEDIA,
            f"presign:get:{key}",
            generate,
            adapter=MEDIA_URL_ADAPTER,
            ttl=ttl * PRESIGN_CACHE_RATIO,
        )

    async def head(self, key: str) -> ObjectMetadata | None:
        try:
            response = await asyncio.to_thread(
                self._client.head_object, Bucket=self._config.bucket_name, Key=key
            )
        except ClientError:
            return None

        return ObjectMetadata(
            size_bytes=response.get("ContentLength", 0),
            content_type=response.get("ContentType", "application/octet-stream"),
        )

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._config.bucket_name, Key=key
        )
        await self._cache.bump(CacheNamespace.MEDIA)

    async def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return

        for batch in batched(keys, S3_DELETE_BATCH_SIZE):
            await asyncio.to_thread(
                self._client.delete_objects,
                Bucket=self._config.bucket_name,
                Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
            )
        await self._cache.bump(CacheNamespace.MEDIA)
