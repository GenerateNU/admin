from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from admin.api.dependencies import get_token_verifier
from admin.core.config import Settings, get_settings
from admin.core.security import LocalTokenVerifier
from admin.main import create_app


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Runs the real lifespan, so this needs Postgres and Redis to be up."""
    app = create_app()
    # Pin the local verifier. Otherwise the suite silently depends on whether the developer's
    # .env has ENTRA_API_CLIENT_ID filled in, and the base64 tokens the tests mint stop working
    # the moment real Entra config is present.
    app.dependency_overrides[get_token_verifier] = LocalTokenVerifier
    with TestClient(app) as test_client:
        yield test_client
