import uuid
from datetime import datetime

from admin.repositories.base import Repository
from admin.schemas.role import PermissionRead, RoleRead

ROLE_SELECT = """
SELECT r.id,
       r.key,
       r.name,
       r.is_system,
       COALESCE(
           array_agg(rp.permission_key ORDER BY rp.permission_key)
               FILTER (WHERE rp.permission_key IS NOT NULL),
           ARRAY[]::varchar[]
       ) AS permissions
FROM roles r
LEFT JOIN role_permissions rp ON rp.role_id = r.id
"""


class RoleRepository(Repository):
    async def list_roles(self) -> list[RoleRead]:
        rows = await self.connection.fetch(f"{ROLE_SELECT} GROUP BY r.id ORDER BY r.name")
        return RoleRead.from_rows(rows)

    async def get_by_id(self, role_id: uuid.UUID) -> RoleRead | None:
        row = await self.connection.fetchrow(
            f"{ROLE_SELECT} WHERE r.id = $1 GROUP BY r.id", role_id
        )
        return RoleRead.from_optional_row(row)

    async def get_by_key(self, key: str) -> RoleRead | None:
        row = await self.connection.fetchrow(f"{ROLE_SELECT} WHERE r.key = $1 GROUP BY r.id", key)
        return RoleRead.from_optional_row(row)

    async def list_permissions(self) -> list[PermissionRead]:
        rows = await self.connection.fetch("SELECT key, description FROM permissions ORDER BY key")
        return PermissionRead.from_rows(rows)

    async def grant(
        self,
        *,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        granted_by: uuid.UUID | None,
        expires_at: datetime | None,
    ) -> uuid.UUID:
        return await self.connection.fetchval(
            """
            INSERT INTO user_roles (user_id, role_id, granted_by, expires_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, role_id)
            DO UPDATE SET expires_at = EXCLUDED.expires_at,
                          granted_by = EXCLUDED.granted_by,
                          granted_at = now()
            RETURNING id
            """,
            user_id,
            role_id,
            granted_by,
            expires_at,
        )

    async def revoke(self, assignment_id: uuid.UUID) -> bool:
        result = await self.connection.execute(
            "DELETE FROM user_roles WHERE id = $1", assignment_id
        )
        return result.endswith("1")

    async def get_assignment_owner(self, assignment_id: uuid.UUID) -> uuid.UUID | None:
        return await self.connection.fetchval(
            "SELECT user_id FROM user_roles WHERE id = $1", assignment_id
        )
