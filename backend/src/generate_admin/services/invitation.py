import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from generate_admin.core.errors import ConflictError, NotFoundError, ValidationError
from generate_admin.domain.access import PermissionSet
from generate_admin.domain.enums import AuditAction
from generate_admin.repositories.audit import AuditRepository
from generate_admin.repositories.invitation import InvitationRepository
from generate_admin.repositories.role import RoleRepository
from generate_admin.repositories.user import UserRepository
from generate_admin.schemas.audit import AuditEntry
from generate_admin.schemas.invitation import InvitationCreate, InvitationCreated, InvitationRead
from generate_admin.schemas.user import UserRead
from generate_admin.services.guards import ensure_can_delegate

TOKEN_BYTES = 32


def generate_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hashlib.sha256(token.encode()).hexdigest()


class InvitationService:
    def __init__(
        self,
        *,
        invitations: InvitationRepository,
        roles: RoleRepository,
        users: UserRepository,
        audit: AuditRepository,
        default_ttl_hours: int,
    ) -> None:
        self._invitations = invitations
        self._roles = roles
        self._users = users
        self._audit = audit
        self._default_ttl_hours = default_ttl_hours

    async def create(
        self,
        *,
        actor: UserRead,
        actor_permissions: PermissionSet,
        payload: InvitationCreate,
    ) -> InvitationCreated:
        email = payload.email.lower()

        if await self._users.get_by_email(email) is not None:
            raise ConflictError("that person is already a member")

        if await self._invitations.find_open_for_email(email) is not None:
            raise ConflictError("an open invitation already exists for that email")

        role = await self._roles.get_by_id(payload.role_id)
        if role is None:
            raise NotFoundError("role does not exist")

        ensure_can_delegate(actor_permissions, role)

        token, token_hash = generate_token()
        ttl_hours = payload.expires_in_hours or self._default_ttl_hours
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        invitation = await self._invitations.create(
            email=email,
            role_id=role.id,
            token_hash=token_hash,
            invited_by=actor.id,
            expires_at=expires_at,
        )

        await self._audit.record(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.INVITATION_CREATED,
                resource_type="invitation",
                resource_id=str(invitation.id),
                after={"email": email, "role_key": role.key},
            )
        )

        return InvitationCreated(invitation=invitation, token=token)

    async def list_open(self) -> list[InvitationRead]:
        return await self._invitations.list_open()

    async def revoke(self, *, actor: UserRead, invitation_id: uuid.UUID) -> None:
        invitation = await self._invitations.get_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("invitation does not exist")

        if not await self._invitations.revoke(invitation_id):
            raise ValidationError("invitation is already accepted or revoked")

        await self._audit.record(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.INVITATION_REVOKED,
                resource_type="invitation",
                resource_id=str(invitation_id),
                before={"email": invitation.email, "status": invitation.status.value},
            )
        )
