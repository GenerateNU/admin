import uuid

from generate_admin.domain.enums import UserStatus
from generate_admin.repositories.base import Repository, required_row
from generate_admin.schemas.role import RoleAssignmentRead
from generate_admin.schemas.user import UserRead

USER_SELECT = """
SELECT u.id,
       u.entra_object_id,
       u.email,
       u.name,
       u.status,
       u.last_login_at,
       u.created_at
FROM users u
"""


class UserRepository(Repository):
    async def get_by_id(self, user_id: uuid.UUID) -> UserRead | None:
        row = await self.connection.fetchrow(f"{USER_SELECT} WHERE u.id = $1", user_id)
        return UserRead.from_optional_row(row)

    async def get_by_entra_object_id(self, entra_object_id: uuid.UUID) -> UserRead | None:
        row = await self.connection.fetchrow(
            f"{USER_SELECT} WHERE u.entra_object_id = $1", entra_object_id
        )
        return UserRead.from_optional_row(row)

    async def get_by_email(self, email: str) -> UserRead | None:
        row = await self.connection.fetchrow(f"{USER_SELECT} WHERE u.email = $1", email.lower())
        return UserRead.from_optional_row(row)

    async def create(self, *, entra_object_id: uuid.UUID, email: str, name: str) -> UserRead:
        created = required_row(
            await self.connection.fetchrow(
                """
                INSERT INTO users (entra_object_id, email, name, last_login_at)
                VALUES ($1, $2, $3, now())
                RETURNING id
                """,
                entra_object_id,
                email.lower(),
                name,
            )
        )
        user = await self.get_by_id(created["id"])
        if user is None:
            raise RuntimeError("user disappeared immediately after insert")
        return user

    async def set_status(self, user_id: uuid.UUID, status: UserStatus) -> UserRead | None:
        await self.connection.execute(
            "UPDATE users SET status = $2 WHERE id = $1", user_id, status.value
        )
        return await self.get_by_id(user_id)

    async def touch_last_login(self, user_id: uuid.UUID) -> None:
        await self.connection.execute(
            """
            UPDATE users
            SET last_login_at = now()
            WHERE id = $1
              AND (last_login_at IS NULL OR last_login_at < now() - interval '1 hour')
            """,
            user_id,
        )

    async def list_role_assignments(self, user_id: uuid.UUID) -> list[RoleAssignmentRead]:
        rows = await self.connection.fetch(
            """
            SELECT ur.id,
                   ur.granted_at,
                   ur.expires_at,
                   jsonb_build_object('id', r.id, 'key', r.key, 'name', r.name) AS role
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = $1
              AND (ur.expires_at IS NULL OR ur.expires_at > now())
            ORDER BY r.name
            """,
            user_id,
        )
        return RoleAssignmentRead.from_rows(rows)

    async def list_granted_permissions(self, user_id: uuid.UUID) -> list[str]:
        rows = await self.connection.fetch(
            """
            SELECT DISTINCT rp.permission_key
            FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            WHERE ur.user_id = $1
              AND (ur.expires_at IS NULL OR ur.expires_at > now())
            """,
            user_id,
        )
        return [row["permission_key"] for row in rows]

    async def count_active_holders_of_role(self, role_key: str) -> int:
        return (
            await self.connection.fetchval(
                """
                SELECT count(DISTINCT ur.user_id)
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                JOIN users u ON u.id = ur.user_id
                WHERE r.key = $1
                  AND u.status = 'active'
                  AND (ur.expires_at IS NULL OR ur.expires_at > now())
                """,
                role_key,
            )
            or 0
        )
