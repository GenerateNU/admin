import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import typer

from admin.core.config import Settings, get_settings
from admin.core.database import DBConnection, create_pool
from admin.core.email import EmailSender, build_email_sender
from admin.domain.permissions import (
    PERMISSION_DESCRIPTIONS,
    ROLE_DEFINITIONS,
    ROLE_DEFINITIONS_BY_KEY,
    Permission,
    SystemRole,
)
from admin.repositories.invitation import InvitationRepository
from admin.repositories.role import RoleRepository
from admin.repositories.user import UserRepository
from admin.services.invitation import generate_token

app = typer.Typer(help="generate-admin management commands")


@app.callback()
def main() -> None:
    """Cli for admin app"""


async def _sync_permissions(connection: DBConnection) -> None:
    await connection.executemany(
        """
        INSERT INTO permissions (key, description)
        VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE SET description = EXCLUDED.description
        """,
        [(permission.value, PERMISSION_DESCRIPTIONS[permission]) for permission in Permission],
    )
    await connection.execute(
        "DELETE FROM permissions WHERE key <> ALL($1::varchar[])",
        [permission.value for permission in Permission],
    )


async def _sync_roles(connection: DBConnection) -> None:
    for definition in ROLE_DEFINITIONS:
        role_id = await connection.fetchval(
            """
            INSERT INTO roles (key, name, is_system)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (key) DO UPDATE SET name = EXCLUDED.name, is_system = TRUE
            RETURNING id
            """,
            definition.key.value,
            definition.name,
        )

        keys = [permission.value for permission in definition.permissions]
        await connection.executemany(
            """
            INSERT INTO role_permissions (role_id, permission_key)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            [(role_id, key) for key in keys],
        )
        await connection.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = $1 AND permission_key <> ALL($2::varchar[])
            """,
            role_id,
            keys,
        )


async def _ensure_owner_invitation(
    connection: DBConnection, settings: Settings, email_sender: EmailSender
) -> None:
    email = settings.initial_owner_email.strip().lower()
    if not email:
        return

    existing_owners = await connection.fetchval(
        """
        SELECT count(*)
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE r.key = $1
        """,
        SystemRole.OWNER.value,
    )
    if existing_owners:
        return

    open_invitation = await connection.fetchval(
        """
        SELECT count(*) FROM invitations
        WHERE email = $1 AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at > now()
        """,
        email,
    )
    if open_invitation:
        return

    role_id = await connection.fetchval(
        "SELECT id FROM roles WHERE key = $1", SystemRole.OWNER.value
    )
    token, token_hash = generate_token()
    await connection.execute(
        """
        INSERT INTO invitations (email, role_id, token_hash, expires_at)
        VALUES ($1, $2, $3, $4)
        """,
        email,
        role_id,
        token_hash,
        datetime.now(UTC) + timedelta(hours=settings.invitation_ttl_hours),
    )
    await email_sender.send_invitation(
        email=email,
        role_name=ROLE_DEFINITIONS_BY_KEY[SystemRole.OWNER].name,
        token=token,
        app_url=settings.frontend_base_url,
    )
    print(f"owner invitation created for {email}")
    print(f"invitation token: {token}")


async def _seed() -> None:
    settings = get_settings()
    pool = await create_pool(settings.database)
    client = httpx.AsyncClient()
    try:
        email_sender = build_email_sender(settings.resend, client)
        async with pool.acquire() as connection, connection.transaction():
            await _sync_permissions(connection)
            await _sync_roles(connection)
            await _ensure_owner_invitation(connection, settings, email_sender)
        print("seed complete")
    finally:
        await client.aclose()
        await pool.close()


@app.command()
def seed() -> None:
    asyncio.run(_seed())


async def _invite(email: str, role_key: str, expires_in_hours: int | None) -> None:
    settings = get_settings()
    pool = await create_pool(settings.database)
    client = httpx.AsyncClient()
    try:
        email_sender = build_email_sender(settings.resend, client)
        async with pool.acquire() as connection, connection.transaction():
            users = UserRepository(connection)
            roles = RoleRepository(connection)
            invitations = InvitationRepository(connection)

            if await users.get_by_email(email) is not None:
                raise typer.BadParameter(f"{email} is already a member")

            role = await roles.get_by_key(role_key)
            if role is None:
                raise typer.BadParameter(f"no role with key {role_key!r} (run `just seed` first)")

            if await invitations.find_open_for_email(email) is not None:
                raise typer.BadParameter(f"an open invitation already exists for {email}")

            token, token_hash = generate_token()
            ttl_hours = expires_in_hours or settings.invitation_ttl_hours
            expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

            await invitations.create(
                email=email,
                role_id=role.id,
                token_hash=token_hash,
                invited_by=None,
                expires_at=expires_at,
            )
            await email_sender.send_invitation(
                email=email, role_name=role.name, token=token, app_url=settings.frontend_base_url
            )

        print(f"invitation created for {email} ({role_key})")
        print(f"invitation token: {token}")
    finally:
        await client.aclose()
        await pool.close()


@app.command()
def invite(
    email: str = typer.Argument(..., help="Email address to invite"),
    role: str = typer.Option(
        ..., "--role", "-r", help="Role key, e.g. owner, admin, or a custom role from `just seed`"
    ),
    expires_in_hours: int | None = typer.Option(
        None, "--expires-in-hours", help="Defaults to INVITATION_TTL_HOURS"
    ),
) -> None:
    """Create an invitation for local/dev use and print the raw token.

    Skips the permission checks InvitationService.create enforces over the API (delegation
    rules, who's allowed to grant what) since this runs with direct DB access, not as a given
    actor. The token is only ever shown here — the database only ever stores its hash.
    """
    asyncio.run(_invite(email.strip().lower(), role, expires_in_hours))


@app.command()
def openapi(output: Path = Path("../openapi.json")) -> None:
    """Write the OpenAPI schema to disk.

    Deliberately does not boot the server: FastAPI can produce the schema from the route table
    alone, so codegen works offline and in CI without Postgres or Redis. Output is stable across
    runs because the route table and Pydantic field order are, which is what the CI drift check
    relies on; keys are left in declaration order rather than sorted so the generated types read
    like the models they came from.
    """
    from admin.main import create_app

    schema = create_app().openapi()
    output.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {output}")


if __name__ == "__main__":
    app()
