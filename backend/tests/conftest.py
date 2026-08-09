from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from admin.core.config import Settings, get_settings
from admin.main import create_app


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Runs the real lifespan, so this needs Postgres and Redis to be up."""
    with TestClient(create_app()) as test_client:
        yield test_client
