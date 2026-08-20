import uuid
from datetime import datetime

from admin.repositories.base import Repository, required_row
from admin.schemas.invitation import InvitationRead

INVITATION_SELECT = """
SELECT i.id,
       i.email,
       i.invited_by,
       i.expires_at,
       i.accepted_at,
       i.revoked_at,
       i.created_at,
       CASE
           WHEN i.accepted_at IS NOT NULL THEN 'accepted'
           WHEN i.revoked_at IS NOT NULL THEN 'revoked'
           WHEN i.expires_at <= now() THEN 'expired'
           ELSE 'pending'
       END AS status,
       jsonb_build_object('id', r.id, 'key', r.key, 'name', r.name) AS role
FROM invitations i
JOIN roles r ON r.id = i.role_id
"""


class InvitationRepository(Repository):
    async def create(
        self,
        *,
        email: str,
        role_id: uuid.UUID,
        token_hash: str,
        invited_by: uuid.UUID | None,
        expires_at: datetime,
    ) -> InvitationRead:
        created = required_row(
            await self.connection.fetchrow(
                """
                INSERT INTO invitations (email, role_id, token_hash, invited_by, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                email.lower(),
                role_id,
                token_hash,
                invited_by,
                expires_at,
            )
        )
        invitation = await self.get_by_id(created["id"])
        if invitation is None:
            raise RuntimeError("invitation disappeared immediately after insert")
        return invitation

    async def get_by_id(self, invitation_id: uuid.UUID) -> InvitationRead | None:
        row = await self.connection.fetchrow(f"{INVITATION_SELECT} WHERE i.id = $1", invitation_id)
        return InvitationRead.from_optional_row(row)

    async def find_open_for_email(self, email: str) -> InvitationRead | None:
        row = await self.connection.fetchrow(
            f"""
            {INVITATION_SELECT}
            WHERE i.email = $1
              AND i.accepted_at IS NULL
              AND i.revoked_at IS NULL
              AND i.expires_at > now()
            """,
            email.lower(),
        )
        return InvitationRead.from_optional_row(row)

    async def find_open_for_email_and_token(
        self, email: str, token_hash: str
    ) -> InvitationRead | None:
        row = await self.connection.fetchrow(
            f"""
            {INVITATION_SELECT}
            WHERE i.email = $1
              AND i.token_hash = $2
              AND i.accepted_at IS NULL
              AND i.revoked_at IS NULL
              AND i.expires_at > now()
            """,
            email.lower(),
            token_hash,
        )
        return InvitationRead.from_optional_row(row)

    async def list_open(self) -> list[InvitationRead]:
        rows = await self.connection.fetch(
            f"""
            {INVITATION_SELECT}
            WHERE i.accepted_at IS NULL AND i.revoked_at IS NULL
            ORDER BY i.created_at DESC
            """
        )
        return InvitationRead.from_rows(rows)

    async def mark_accepted(self, invitation_id: uuid.UUID) -> None:
        await self.connection.execute(
            "UPDATE invitations SET accepted_at = now() WHERE id = $1", invitation_id
        )

    async def revoke(self, invitation_id: uuid.UUID) -> bool:
        result = await self.connection.execute(
            """
            UPDATE invitations
            SET revoked_at = now()
            WHERE id = $1 AND accepted_at IS NULL AND revoked_at IS NULL
            """,
            invitation_id,
        )
        return result.endswith("1")
