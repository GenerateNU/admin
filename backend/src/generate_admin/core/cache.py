import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, Protocol

from pydantic import TypeAdapter
from redis.asyncio import Redis

from generate_admin.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TTL_SECONDS = 60.0
KEY_PREFIX = "generate-admin"


class CacheNamespace(StrEnum):
    CONTENT = "content"
    MEDIA = "media"
    ORGANIZATION = "organization"
    ROLES = "roles"


Loader = Callable[[], Awaitable[Any]]


class Cache(Protocol):
    async def fetch(
        self,
        namespace: CacheNamespace,
        key: str,
        loader: Loader,
        *,
        adapter: TypeAdapter[Any],
        ttl: float | None = None,
    ) -> Any: ...

    async def bump(self, namespace: CacheNamespace) -> None: ...

    async def version(self, namespace: CacheNamespace) -> int: ...

    async def close(self) -> None: ...


class SingleFlight:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def lock_for(self, key: str) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(key, asyncio.Lock())


class RedisCache:
    def __init__(self, client: Redis, *, default_ttl: float = DEFAULT_TTL_SECONDS) -> None:
        self._client = client
        self._default_ttl = default_ttl
        self._flight = SingleFlight()

    def _version_key(self, namespace: CacheNamespace) -> str:
        return f"{KEY_PREFIX}:version:{namespace.value}"

    async def version(self, namespace: CacheNamespace) -> int:
        raw = await self._client.get(self._version_key(namespace))
        return int(raw) if raw else 0

    async def bump(self, namespace: CacheNamespace) -> None:
        await self._client.incr(self._version_key(namespace))

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch(
        self,
        namespace: CacheNamespace,
        key: str,
        loader: Loader,
        *,
        adapter: TypeAdapter[Any],
        ttl: float | None = None,
    ) -> Any:
        version = await self.version(namespace)
        qualified = f"{KEY_PREFIX}:{namespace.value}:v{version}:{key}"

        cached = await self._client.get(qualified)
        if cached is not None:
            return adapter.validate_json(cached)

        lock = await self._flight.lock_for(qualified)
        async with lock:
            cached = await self._client.get(qualified)
            if cached is not None:
                return adapter.validate_json(cached)

            value = await loader()
            await self._client.set(
                qualified,
                adapter.dump_json(value),
                ex=int(ttl or self._default_ttl),
            )
            return value


async def build_cache(redis_url: str, *, default_ttl: float = DEFAULT_TTL_SECONDS) -> Cache:
    if not redis_url:
        raise RuntimeError("REDIS_URL is required")

    client: Redis = Redis.from_url(redis_url, decode_responses=False)
    try:
        await client.ping()
    except Exception as error:
        await client.aclose()
        raise RuntimeError(f"could not connect to redis at {redis_url}") from error

    logger.info("cache_redis", url=redis_url)
    return RedisCache(client, default_ttl=default_ttl)
