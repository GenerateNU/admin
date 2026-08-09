from fastapi.testclient import TestClient


def test_health_reports_database_up(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_app_wires_cache_and_storage(client: TestClient) -> None:
    state = client.app.state

    assert type(state.cache).__name__ == "RedisCache"
    assert state.storage is not None
