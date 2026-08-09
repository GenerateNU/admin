import uuid
from datetime import datetime

from admin.repositories.base import ConditionSet, Repository
from admin.schemas.audit import AuditEntry, AuditLogRead
from admin.schemas.base import CursorParams

AUDIT_COLUMNS = """
id, actor_id, actor_email, action, resource_type, resource_id,
before, after, created_at
"""


class AuditRepository(Repository):
    async def record(self, entry: AuditEntry) -> None:
        await self.connection.execute(
            """
            INSERT INTO audit_logs
                (actor_id, actor_email, action, resource_type, resource_id,
                 before, after)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            entry.actor_id,
            entry.actor_email,
            entry.action.value,
            entry.resource_type,
            entry.resource_id,
            entry.before,
            entry.after,
        )

    async def list_entries(
        self,
        params: CursorParams,
        *,
        actor_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> list[AuditLogRead]:
        conditions = ConditionSet()
        conditions.add_if(actor_id is not None, "actor_id = {0}", actor_id)
        conditions.add_if(resource_type is not None, "resource_type = {0}", resource_type)
        conditions.add_if(resource_id is not None, "resource_id = {0}", resource_id)

        after = params.decoded()
        if after is not None:
            conditions.add(
                "(created_at, id) < ({0}, {1})",
                datetime.fromisoformat(after[0]),
                uuid.UUID(after[1]),
            )

        rows = await self.connection.fetch(
            f"""
            SELECT {AUDIT_COLUMNS}
            FROM audit_logs
            {conditions.where}
            ORDER BY created_at DESC, id DESC
            LIMIT ${conditions.next_index}
            """,
            *conditions.params,
            params.fetch_limit,
        )
        return AuditLogRead.from_rows(rows)
