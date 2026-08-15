from admin.domain.access import PermissionSet, ResolvedAccess
from admin.domain.enums import (
    AccessRequestStatus,
    AccessState,
    AuditAction,
    UserStatus,
)
from admin.repositories.access_request import AccessRequestRepository
from admin.repositories.audit import AuditRepository
from admin.repositories.invitation import InvitationRepository
from admin.repositories.role import RoleRepository
from admin.repositories.user import UserRepository
from admin.schemas.audit import AuditEntry
from admin.schemas.invitation import InvitationRead
from admin.schemas.session import Identity, Session
from admin.schemas.user import UserRead


class AccessService:
    def __init__(
        self,
        *,
        users: UserRepository,
        invitations: InvitationRepository,
        access_requests: AccessRequestRepository,
        roles: RoleRepository,
        audit: AuditRepository,
    ) -> None:
        self._users = users
        self._invitations = invitations
        self._access_requests = access_requests
        self._roles = roles
        self._audit = audit

    async def resolve(self, identity: Identity) -> ResolvedAccess:
        user = await self._users.get_by_entra_object_id(identity.entra_object_id)

        if user is None:
            invitation = await self._invitations.find_open_for_email(identity.email)
            if invitation is not None:
                user = await self._accept_invitation(identity, invitation)

        if user is None:
            return ResolvedAccess(
                session=Session(
                    access_state=await self._state_without_account(identity),
                    identity=identity,
                ),
                permissions=PermissionSet.from_keys([]),
            )

        return await self._session_for_user(identity, user)

    async def _state_without_account(self, identity: Identity) -> AccessState:
        request = await self._access_requests.find_latest_for_email(identity.email)
        if request is None:
            return AccessState.NO_ACCESS
        if request.status is AccessRequestStatus.PENDING:
            return AccessState.PENDING
        if request.status is AccessRequestStatus.DENIED:
            return AccessState.DENIED
        return AccessState.NO_ACCESS

    async def _session_for_user(self, identity: Identity, user: UserRead) -> ResolvedAccess:
        if user.status is UserStatus.SUSPENDED:
            return ResolvedAccess(
                session=Session(access_state=AccessState.SUSPENDED, identity=identity, user=user),
                permissions=PermissionSet.from_keys([]),
            )

        await self._users.touch_last_login(user.id)

        permissions = PermissionSet.from_keys(await self._users.list_granted_permissions(user.id))
        assignments = await self._users.list_role_assignments(user.id)
        user = user.model_copy(update={"role_assignments": assignments})

        return ResolvedAccess(
            session=Session(
                access_state=AccessState.NO_ROLES if permissions.is_empty else AccessState.ACTIVE,
                identity=identity,
                user=user,
                permissions=permissions.keys,
            ),
            permissions=permissions,
        )

    async def _accept_invitation(self, identity: Identity, invitation: InvitationRead) -> UserRead:
        user = await self._users.create(
            entra_object_id=identity.entra_object_id,
            email=identity.email,
            name=identity.name,
        )

        await self._roles.grant(
            user_id=user.id,
            role_id=invitation.role.id,
            granted_by=invitation.invited_by,
            expires_at=None,
        )
        await self._invitations.mark_accepted(invitation.id)

        await self._audit.record_many(
            [
                AuditEntry(
                    actor_id=user.id,
                    actor_email=user.email,
                    action=AuditAction.INVITATION_ACCEPTED,
                    resource_type="invitation",
                    resource_id=str(invitation.id),
                    after={"user_id": str(user.id), "role_key": invitation.role.key},
                ),
                AuditEntry(
                    actor_id=user.id,
                    actor_email=user.email,
                    action=AuditAction.USER_PROVISIONED,
                    resource_type="user",
                    resource_id=str(user.id),
                    after={"email": user.email, "source": "invitation"},
                ),
            ]
        )
        return user
