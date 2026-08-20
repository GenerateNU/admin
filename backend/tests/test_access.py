import asyncio
import base64
import hashlib
import json
import uuid

from fastapi.testclient import TestClient

from admin.core.config import Settings
from admin.core.database import create_pool


def local_token(email: str, object_id: uuid.UUID) -> str:
    claims = json.dumps({"oid": str(object_id), "email": email, "name": "Test Person"})
    return base64.urlsafe_b64encode(claims.encode()).decode().rstrip("=")


def auth_header(email: str, object_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {local_token(email, object_id)}"}


async def _create_invitation(settings: Settings, *, email: str, token: str) -> None:
    pool = await create_pool(settings.database)
    try:
        async with pool.acquire() as connection:
            role_id = await connection.fetchval(
                """
                INSERT INTO roles (key, name, is_system)
                VALUES ($1, $2, FALSE)
                ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                "test-invite-role",
                "Test Invite Role",
            )
            await connection.execute(
                """
                INSERT INTO invitations (email, role_id, token_hash, expires_at)
                VALUES ($1, $2, $3, now() + interval '1 hour')
                """,
                email,
                role_id,
                hashlib.sha256(token.encode()).hexdigest(),
            )
    finally:
        await pool.close()


def create_invitation(settings: Settings, *, email: str, token: str) -> None:
    asyncio.run(_create_invitation(settings, email=email, token=token))


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


def test_invited_stranger_sees_invited_state(client: TestClient, settings: Settings) -> None:
    object_id = uuid.uuid4()
    email = f"{object_id}@example.com"
    create_invitation(settings, email=email, token=f"token-{object_id}")

    response = client.get("/api/v1/session", headers=auth_header(email, object_id))

    assert response.status_code == 200
    body = response.json()
    assert body["access_state"] == "invited"
    assert body["user"] is None


def test_wrong_token_does_not_accept_the_invitation(client: TestClient, settings: Settings) -> None:
    object_id = uuid.uuid4()
    email = f"{object_id}@example.com"
    create_invitation(settings, email=email, token=f"correct-{object_id}")

    response = client.post(
        "/api/v1/session/accept-invitation",
        headers=auth_header(email, object_id),
        json={"token": "wrong-token"},
    )

    assert response.status_code == 404

    session = client.get("/api/v1/session", headers=auth_header(email, object_id))
    assert session.json()["access_state"] == "invited"


def test_accept_invitation_provisions_the_user(client: TestClient, settings: Settings) -> None:
    object_id = uuid.uuid4()
    email = f"{object_id}@example.com"
    token = f"correct-{object_id}"
    create_invitation(settings, email=email, token=token)

    response = client.post(
        "/api/v1/session/accept-invitation",
        headers=auth_header(email, object_id),
        json={"token": token},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == email

    session = client.get("/api/v1/session", headers=auth_header(email, object_id))
    assert session.json()["user"]["email"] == email

    repeated = client.post(
        "/api/v1/session/accept-invitation",
        headers=auth_header(email, object_id),
        json={"token": token},
    )
    assert repeated.status_code == 404


def test_unprovisioned_caller_cannot_read_roles(client: TestClient) -> None:
    object_id = uuid.uuid4()
    headers = auth_header(f"{object_id}@example.com", object_id)

    response = client.get("/api/v1/roles", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "account_not_provisioned"
