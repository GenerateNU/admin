import asyncio
import uuid

import pytest
from pydantic import TypeAdapter

from admin.core.cache import Cache, CacheNamespace, build_cache
from admin.core.config import Settings

STRING_ADAPTER = TypeAdapter(str)


@pytest.fixture
async def cache(settings: Settings) -> Cache:
    return await build_cache(settings.redis_url)


def unique_key() -> str:
    return f"test:{uuid.uuid4().hex}"


async def test_build_cache_requires_a_url() -> None:
    with pytest.raises(RuntimeError, match="REDIS_URL is required"):
        await build_cache("")


async def test_second_fetch_is_served_from_cache(cache: Cache) -> None:
    key = unique_key()
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return "value"

    first = await cache.fetch(CacheNamespace.CONTENT, key, loader, adapter=STRING_ADAPTER)
    second = await cache.fetch(CacheNamespace.CONTENT, key, loader, adapter=STRING_ADAPTER)

    assert first == second == "value"
    assert calls == 1


async def test_concurrent_misses_run_the_loader_once(cache: Cache) -> None:
    key = unique_key()
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return "value"

    results = await asyncio.gather(
        *(
            cache.fetch(CacheNamespace.CONTENT, key, loader, adapter=STRING_ADAPTER)
            for _ in range(10)
        )
    )

    assert results == ["value"] * 10
    assert calls == 1


async def test_unreachable_redis_still_builds_a_cache() -> None:
    """Booting without a reachable cache is slow; refusing to boot is an outage."""
    unreachable = await build_cache("redis://127.0.0.1:1/0")
    assert unreachable is not None
    await unreachable.close()


async def test_fetch_falls_back_to_the_loader_when_redis_is_down() -> None:
    unreachable = await build_cache("redis://127.0.0.1:1/0")
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return "value"

    try:
        first = await unreachable.fetch(
            CacheNamespace.CONTENT, unique_key(), loader, adapter=STRING_ADAPTER
        )
        second = await unreachable.fetch(
            CacheNamespace.CONTENT, unique_key(), loader, adapter=STRING_ADAPTER
        )
    finally:
        await unreachable.close()

    # Every call recomputes, but nothing raises.
    assert first == second == "value"
    assert calls == 2


async def test_bump_does_not_raise_when_redis_is_down() -> None:
    unreachable = await build_cache("redis://127.0.0.1:1/0")
    try:
        await unreachable.bump(CacheNamespace.ROLES)
    finally:
        await unreachable.close()


async def test_bump_invalidates_the_whole_namespace(cache: Cache) -> None:
    key = unique_key()
    calls = 0

    async def loader() -> str:
        nonlocal calls
        calls += 1
        return f"value-{calls}"

    before = await cache.version(CacheNamespace.ROLES)
    assert await cache.fetch(CacheNamespace.ROLES, key, loader, adapter=STRING_ADAPTER) == "value-1"

    await cache.bump(CacheNamespace.ROLES)

    assert await cache.version(CacheNamespace.ROLES) == before + 1
    assert await cache.fetch(CacheNamespace.ROLES, key, loader, adapter=STRING_ADAPTER) == "value-2"
