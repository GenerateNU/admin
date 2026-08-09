import asyncio
import sys
from datetime import UTC, datetime, timedelta

import asyncpg

from generate_admin.core.config import Settings, get_settings
from generate_admin.core.database import create_pool
from generate_admin.domain.permissions import (
    PERMISSION_DESCRIPTIONS,
    ROLE_DEFINITIONS,
    Permission,
    SystemRole,
)
from generate_admin.services.invitation import generate_token


async def sync_permissions(connection: asyncpg.Connection) -> None:
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


async def sync_roles(connection: asyncpg.Connection) -> None:
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


async def ensure_owner_invitation(connection: asyncpg.Connection, settings: Settings) -> None:
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
    print(f"owner invitation created for {email}")
    print(f"invitation token: {token}")


async def seed() -> None:
    settings = get_settings()
    pool = await create_pool(settings.database)
    try:
        async with pool.acquire() as connection, connection.transaction():
            await sync_permissions(connection)
            await sync_roles(connection)
            await ensure_owner_invitation(connection, settings)
        print("seed complete")
    finally:
        await pool.close()


COMMANDS = {"seed": seed}


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"usage: python -m generate_admin.cli [{'|'.join(COMMANDS)}]")
        raise SystemExit(1)
    asyncio.run(handler())


if __name__ == "__main__":
    main()
