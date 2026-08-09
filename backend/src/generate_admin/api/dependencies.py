from collections.abc import AsyncIterator
from typing import Annotated

import asyncpg
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from generate_admin.core.cache import Cache as CacheProtocol
from generate_admin.core.config import Settings, get_settings
from generate_admin.core.security import TokenVerifier
from generate_admin.core.storage import S3Storage
from generate_admin.schemas.session import Identity

bearer_scheme = HTTPBearer(auto_error=True)


async def get_connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    """One connection and one transaction per request; rolls back on error."""
    pool: asyncpg.Pool = request.app.state.pool
    async with pool.acquire() as connection, connection.transaction():
        yield connection


def get_read_cache(request: Request) -> CacheProtocol:
    return request.app.state.cache


def get_storage(request: Request) -> S3Storage:
    return request.app.state.storage


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


Connection = Annotated[asyncpg.Connection, Depends(get_connection)]
Cache = Annotated[CacheProtocol, Depends(get_read_cache)]
Storage = Annotated[S3Storage, Depends(get_storage)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_identity(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> Identity:
    return await verifier.verify(credentials.credentials)


CurrentIdentity = Annotated[Identity, Depends(get_identity)]

# Add repository and service factories here as the app grows, e.g.
#
#   def get_thing_repository(connection: Connection) -> ThingRepository:
#       return ThingRepository(connection)
#
#   Things = Annotated[ThingRepository, Depends(get_thing_repository)]
