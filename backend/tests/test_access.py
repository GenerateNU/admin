import base64
import json
import uuid

from fastapi.testclient import TestClient


def local_token(email: str, object_id: uuid.UUID) -> str:
    claims = json.dumps({"oid": str(object_id), "email": email, "name": "Test Person"})
    return base64.urlsafe_b64encode(claims.encode()).decode().rstrip("=")


def auth_header(email: str, object_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {local_token(email, object_id)}"}


def test_session_requires_a_token(client: TestClient) -> None:
    response = client.get("/api/v1/session")

    assert response.status_code == 401


def test_stranger_gets_a_no_access_session(client: TestClient) -> None:
    object_id = uuid.uuid4()
    headers = auth_header(f"{object_id}@example.com", object_id)

    response = client.get("/api/v1/session", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["access_state"] == "no_access"
    assert body["user"] is None
    assert body["permissions"] == []


def test_access_request_moves_the_session_to_pending(client: TestClient) -> None:
    object_id = uuid.uuid4()
    headers = auth_header(f"{object_id}@example.com", object_id)

    created = client.post(
        "/api/v1/session/access-request", headers=headers, json={"message": "let me in"}
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"

    repeated = client.post("/api/v1/session/access-request", headers=headers, json={})

    assert repeated.status_code == 201
    assert repeated.json()["id"] == created.json()["id"]

    session = client.get("/api/v1/session", headers=headers)

    assert session.json()["access_state"] == "pending"


def test_unprovisioned_caller_cannot_read_roles(client: TestClient) -> None:
    object_id = uuid.uuid4()
    headers = auth_header(f"{object_id}@example.com", object_id)

    response = client.get("/api/v1/roles", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "account_not_provisioned"
