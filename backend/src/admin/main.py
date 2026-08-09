from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from admin.api.router import api_router, root_router
from admin.core.cache import build_cache
from admin.core.config import Settings, get_settings
from admin.core.database import create_pool
from admin.core.errors import DomainError
from admin.core.logging import configure_logging, get_logger
from admin.core.openapi import operation_id_for
from admin.core.security import build_token_verifier
from admin.core.storage import S3Storage

logger = get_logger(__name__)

HTTP_TIMEOUT_SECONDS = 10.0


def verify_production_readiness(settings: Settings) -> None:
    if settings.app.is_production and not settings.entra.is_configured:
        raise RuntimeError("ENTRA_TENANT_ID and ENTRA_API_CLIENT_ID are required in production")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    verify_production_readiness(settings)

    pool = await create_pool(settings.database)
    client = httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    cache = await build_cache(settings.redis_url)

    app.state.settings = settings
    app.state.pool = pool
    app.state.http_client = client
    app.state.cache = cache
    app.state.storage = S3Storage(settings.storage, cache)
    app.state.token_verifier = build_token_verifier(settings.entra, client)

    logger.info("application_started", environment=settings.app.environment.value)

    try:
        yield
    finally:
        await client.aclose()
        await cache.close()
        await pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app)

    app = FastAPI(
        title=settings.app.name,
        version="0.1.0",
        lifespan=lifespan,
        generate_unique_id_function=operation_id_for,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"code": error.code, "message": error.message, "details": error.details},
        )

    app.include_router(root_router)
    app.include_router(api_router)
    return app


app = create_app()
