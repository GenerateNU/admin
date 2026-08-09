import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from admin.core.config import DatabaseConfig

# Pool.acquire() yields a PoolConnectionProxy, which forwards to Connection at runtime via
# metaclass delegation but is not a subclass of it. Anything that just runs queries should
# accept either.
type DBConnection = asyncpg.Connection | asyncpg.pool.PoolConnectionProxy

ASYNCPG_SCHEME = "postgresql://"
SQLALCHEMY_SCHEME = "postgresql+asyncpg://"


def to_asyncpg_dsn(url: str) -> str:
    return url.replace(SQLALCHEMY_SCHEME, ASYNCPG_SCHEME, 1)


async def _register_codecs(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def create_pool(config: DatabaseConfig) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn=to_asyncpg_dsn(config.url.get_secret_value()),
        min_size=1,
        max_size=config.pool_size + config.max_overflow,
        init=_register_codecs,
    )
    if pool is None:
        raise RuntimeError("failed to create database pool")
    return pool


@asynccontextmanager
async def transaction(pool: asyncpg.Pool) -> AsyncGenerator[DBConnection]:
    async with pool.acquire() as connection, connection.transaction():
        yield connection
