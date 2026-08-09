import uuid

from generate_admin.domain.enums import AccessRequestStatus
from generate_admin.repositories.base import Repository, required_row
from generate_admin.schemas.access_request import AccessRequestRead

ACCESS_REQUEST_COLUMNS = """
id, email, entra_object_id, name, message, status,
reviewed_by, reviewed_at, decision_note, created_at
"""


class AccessRequestRepository(Repository):
    async def create(
        self,
        *,
        email: str,
        entra_object_id: uuid.UUID,
        name: str,
        message: str | None,
    ) -> AccessRequestRead:
        row = await self.connection.fetchrow(
            f"""
            INSERT INTO access_requests (email, entra_object_id, name, message)
            VALUES ($1, $2, $3, $4)
            RETURNING {ACCESS_REQUEST_COLUMNS}
            """,
            email.lower(),
            entra_object_id,
            name,
            message,
        )
        return AccessRequestRead.from_row(required_row(row))

    async def get_by_id(self, request_id: uuid.UUID) -> AccessRequestRead | None:
        row = await self.connection.fetchrow(
            f"SELECT {ACCESS_REQUEST_COLUMNS} FROM access_requests WHERE id = $1", request_id
        )
        return AccessRequestRead.from_optional_row(row)

    async def find_latest_for_email(self, email: str) -> AccessRequestRead | None:
        row = await self.connection.fetchrow(
            f"""
            SELECT {ACCESS_REQUEST_COLUMNS}
            FROM access_requests
            WHERE email = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            email.lower(),
        )
        return AccessRequestRead.from_optional_row(row)

    async def list_by_status(self, status: AccessRequestStatus) -> list[AccessRequestRead]:
        rows = await self.connection.fetch(
            f"""
            SELECT {ACCESS_REQUEST_COLUMNS}
            FROM access_requests
            WHERE status = $1
            ORDER BY created_at ASC
            """,
            status.value,
        )
        return AccessRequestRead.from_rows(rows)

    async def record_decision(
        self,
        *,
        request_id: uuid.UUID,
        status: AccessRequestStatus,
        reviewed_by: uuid.UUID,
        note: str | None,
    ) -> AccessRequestRead | None:
        row = await self.connection.fetchrow(
            f"""
            UPDATE access_requests
            SET status = $2, reviewed_by = $3, reviewed_at = now(), decision_note = $4
            WHERE id = $1 AND status = 'pending'
            RETURNING {ACCESS_REQUEST_COLUMNS}
            """,
            request_id,
            status.value,
            reviewed_by,
            note,
        )
        return AccessRequestRead.from_optional_row(row)
