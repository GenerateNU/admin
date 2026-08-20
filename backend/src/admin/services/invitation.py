import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from admin.core.audit import AuditLog
from admin.core.email import EmailSender
from admin.core.errors import ConflictError, NotFoundError, ValidationError
from admin.domain.access import PermissionSet
from admin.domain.enums import AuditAction
from admin.repositories.invitation import InvitationRepository
from admin.repositories.role import RoleRepository
from admin.repositories.user import UserRepository
from admin.schemas.audit import AuditEntry
from admin.schemas.invitation import InvitationCreate, InvitationCreated, InvitationRead
from admin.schemas.user import UserRead
from admin.services.guards import ensure_can_delegate

TOKEN_BYTES = 32


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hash_token(token)


class InvitationService:
    def __init__(
        self,
        *,
        invitations: InvitationRepository,
        roles: RoleRepository,
        users: UserRepository,
        audit: AuditLog,
        email_sender: EmailSender,
        default_ttl_hours: int,
        frontend_base_url: str,
    ) -> None:
        self._invitations = invitations
        self._roles = roles
        self._users = users
        self._audit = audit
        self._email_sender = email_sender
        self._default_ttl_hours = default_ttl_hours
        self._frontend_base_url = frontend_base_url

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

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.INVITATION_CREATED,
                resource_type="invitation",
                resource_id=str(invitation.id),
                after={"email": email, "role_key": role.key},
            )
        )

        await self._email_sender.send_invitation(
            email=email, role_name=role.name, token=token, app_url=self._frontend_base_url
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

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.INVITATION_REVOKED,
                resource_type="invitation",
                resource_id=str(invitation_id),
                before={"email": invitation.email, "status": invitation.status.value},
            )
        )
