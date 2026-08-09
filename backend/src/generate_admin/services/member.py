import uuid

from generate_admin.core.errors import NotFoundError
from generate_admin.domain.access import PermissionSet
from generate_admin.domain.enums import AuditAction
from generate_admin.repositories.audit import AuditRepository
from generate_admin.repositories.role import RoleRepository
from generate_admin.repositories.user import UserRepository
from generate_admin.schemas.audit import AuditEntry
from generate_admin.schemas.role import RoleGrantRequest
from generate_admin.schemas.user import UserRead
from generate_admin.services.guards import ensure_can_delegate, ensure_not_last_owner


class MemberService:
    def __init__(
        self,
        *,
        users: UserRepository,
        roles: RoleRepository,
        audit: AuditRepository,
    ) -> None:
        self._users = users
        self._roles = roles
        self._audit = audit

    async def get_member(self, user_id: uuid.UUID) -> UserRead:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("member does not exist")
        assignments = await self._users.list_role_assignments(user_id)
        return user.model_copy(update={"role_assignments": assignments})

    async def grant_role(
        self,
        *,
        actor: UserRead,
        actor_permissions: PermissionSet,
        user_id: uuid.UUID,
        payload: RoleGrantRequest,
    ) -> UserRead:
        if await self._users.get_by_id(user_id) is None:
            raise NotFoundError("member does not exist")

        role = await self._roles.get_by_id(payload.role_id)
        if role is None:
            raise NotFoundError("role does not exist")

        ensure_can_delegate(actor_permissions, role)

        await self._roles.grant(
            user_id=user_id,
            role_id=role.id,
            granted_by=actor.id,
            expires_at=payload.expires_at,
        )

        await self._audit.record(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.ROLE_GRANTED,
                resource_type="user",
                resource_id=str(user_id),
                after={
                    "role_key": role.key,
                    "expires_at": payload.expires_at.isoformat() if payload.expires_at else None,
                },
            )
        )
        return await self.get_member(user_id)

    async def revoke_role(self, *, actor: UserRead, assignment_id: uuid.UUID) -> UserRead:
        user_id = await self._roles.get_assignment_owner(assignment_id)
        if user_id is None:
            raise NotFoundError("role assignment does not exist")

        member = await self.get_member(user_id)
        assignment = next(
            (item for item in member.role_assignments if item.id == assignment_id), None
        )
        if assignment is None:
            raise NotFoundError("role assignment does not exist")

        await ensure_not_last_owner(self._users, assignment.role.key)
        await self._roles.revoke(assignment_id)

        await self._audit.record(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.ROLE_REVOKED,
                resource_type="user",
                resource_id=str(user_id),
                before={"role_key": assignment.role.key},
            )
        )
        return await self.get_member(user_id)
