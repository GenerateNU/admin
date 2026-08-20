import uuid
from datetime import datetime

from admin.repositories.base import Repository, required_row
from admin.schemas.branch import BranchDraftRecord, BranchRecord

BRANCH_DRAFT_SELECT = """
SELECT id, name, description, icon_key, color, position, created_at, updated_at
FROM branch_drafts
"""

BRANCH_SELECT = """
SELECT id, name, description, icon_key, color, position
FROM branches
"""


class BranchDraftRepository(Repository):
    async def list_all(self) -> list[BranchDraftRecord]:
        rows = await self.connection.fetch(f"{BRANCH_DRAFT_SELECT} ORDER BY position, created_at")
        return BranchDraftRecord.from_rows(rows)

    async def get_by_id(self, branch_id: uuid.UUID) -> BranchDraftRecord | None:
        row = await self.connection.fetchrow(f"{BRANCH_DRAFT_SELECT} WHERE id = $1", branch_id)
        return BranchDraftRecord.from_optional_row(row)

    async def create(
        self,
        *,
        name: str,
        description: str | None,
        icon_key: str,
        color: str,
        position: int,
    ) -> BranchDraftRecord:
        created = required_row(
            await self.connection.fetchrow(
                """
                INSERT INTO branch_drafts (name, description, icon_key, color, position)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                name,
                description,
                icon_key,
                color,
                position,
            )
        )
        draft = await self.get_by_id(created["id"])
        if draft is None:
            raise RuntimeError("branch draft disappeared immediately after insert")
        return draft

    async def update(
        self,
        branch_id: uuid.UUID,
        *,
        name: str | None,
        description: str | None,
        icon_key: str | None,
        color: str | None,
        position: int | None,
    ) -> BranchDraftRecord | None:
        row = await self.connection.fetchrow(
            """
            UPDATE branch_drafts
            SET name        = COALESCE($2, name),
                description = COALESCE($3, description),
                icon_key    = COALESCE($4, icon_key),
                color       = COALESCE($5, color),
                position    = COALESCE($6, position),
                updated_at  = now()
            WHERE id = $1
            RETURNING id
            """,
            branch_id,
            name,
            description,
            icon_key,
            color,
            position,
        )
        if row is None:
            return None
        return await self.get_by_id(row["id"])

    async def delete(self, branch_id: uuid.UUID) -> bool:
        result = await self.connection.execute("DELETE FROM branch_drafts WHERE id = $1", branch_id)
        return result.endswith("1")

    async def reorder(self, ordered_ids: list[uuid.UUID]) -> None:
        await self.connection.executemany(
            "UPDATE branch_drafts SET position = $2, updated_at = now() WHERE id = $1",
            [(branch_id, position) for position, branch_id in enumerate(ordered_ids)],
        )

    async def replace_all(self, branches: list[BranchRecord]) -> None:
        await self.connection.execute("DELETE FROM branch_drafts")
        if not branches:
            return
        await self.connection.executemany(
            """
            INSERT INTO branch_drafts (id, name, description, icon_key, color, position)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [(b.id, b.name, b.description, b.icon_key, b.color, b.position) for b in branches],
        )


class BranchRepository(Repository):
    async def list_all(self) -> list[BranchRecord]:
        rows = await self.connection.fetch(f"{BRANCH_SELECT} ORDER BY position")
        return BranchRecord.from_rows(rows)

    async def last_published_at(self) -> datetime | None:
        return await self.connection.fetchval("SELECT max(created_at) FROM branches")

    async def replace_all(self, drafts: list[BranchDraftRecord]) -> None:
        await self.connection.execute("DELETE FROM branches")
        if not drafts:
            return
        await self.connection.executemany(
            """
            INSERT INTO branches (id, name, description, icon_key, color, position)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [(d.id, d.name, d.description, d.icon_key, d.color, d.position) for d in drafts],
        )
