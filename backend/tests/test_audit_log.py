import uuid
from contextlib import asynccontextmanager

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient

from admin.api.dependencies import Audit, Connection, get_connection
from admin.core.audit import AuditLog
from admin.core.database import create_pool
from admin.domain.enums import AuditAction
from admin.schemas.audit import AuditEntry


def entry(resource_id: str) -> AuditEntry:
    return AuditEntry(
        action=AuditAction.USER_PROVISIONED,
        resource_type="test",
        resource_id=resource_id,
    )


@pytest.fixture
def app(settings) -> FastAPI:
    router = APIRouter()

    @router.post("/write/{resource_id}")
    async def write(resource_id: str, audit: Audit) -> dict[str, str]:
        audit.add(entry(resource_id), entry(resource_id))
        return {"ok": resource_id}

    @router.post("/write-then-fail/{resource_id}")
    async def write_then_fail(resource_id: str, audit: Audit) -> dict[str, str]:
        audit.add(entry(resource_id))
        raise RuntimeError("boom")

    @router.get("/count/{resource_id}")
    async def count(resource_id: str, connection: Connection) -> dict[str, int]:
        rows = await connection.fetchval(
            "SELECT count(*) FROM audit_logs WHERE resource_type='test' AND resource_id=$1",
            resource_id,
        )
        return {"count": rows}

    @asynccontextmanager
    async def lifespan(instance: FastAPI):
        instance.state.pool = await create_pool(settings.database)
        yield
        await instance.state.pool.close()

    application = FastAPI(lifespan=lifespan)

    async def connection_override(request: Request):
        async with request.app.state.pool.acquire() as connection, connection.transaction():
            yield connection

    application.dependency_overrides[get_connection] = connection_override
    application.include_router(router)
    return application


def test_entries_flush_inside_the_request_transaction(app: FastAPI) -> None:
    resource_id = str(uuid.uuid4())
    with TestClient(app) as client:
        assert client.post(f"/write/{resource_id}").status_code == 200
        assert client.get(f"/count/{resource_id}").json()["count"] == 2


def test_entries_roll_back_when_the_request_fails(app: FastAPI) -> None:
    resource_id = str(uuid.uuid4())
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f"/write-then-fail/{resource_id}")
        assert client.get(f"/count/{resource_id}").json()["count"] == 0


def test_nothing_is_written_when_no_entries_are_added(app: FastAPI) -> None:
    resource_id = str(uuid.uuid4())
    with TestClient(app) as client:
        assert client.get(f"/count/{resource_id}").json()["count"] == 0


def test_add_accepts_multiple_entries() -> None:
    log = AuditLog()
    log.add(entry("a"))
    log.add(entry("b"), entry("c"))
    assert [item.resource_id for item in log.entries] == ["a", "b", "c"]
