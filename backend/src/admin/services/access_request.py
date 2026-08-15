import uuid

from admin.core.audit import AuditLog
from admin.core.errors import ConflictError, NotFoundError, ValidationError
from admin.domain.access import PermissionSet
from admin.domain.enums import AccessRequestStatus, AuditAction
from admin.repositories.access_request import AccessRequestRepository
from admin.repositories.role import RoleRepository
from admin.repositories.user import UserRepository
from admin.schemas.access_request import (
    AccessRequestApproval,
    AccessRequestCreate,
    AccessRequestDenial,
    AccessRequestRead,
)
from admin.schemas.audit import AuditEntry
from admin.schemas.session import Identity
from admin.schemas.user import UserRead
from admin.services.guards import ensure_can_delegate


class AccessRequestService:
    def __init__(
        self,
        *,
        access_requests: AccessRequestRepository,
        users: UserRepository,
        roles: RoleRepository,
        audit: AuditLog,
    ) -> None:
        self._access_requests = access_requests
        self._users = users
        self._roles = roles
        self._audit = audit

    async def create(
        self, *, identity: Identity, payload: AccessRequestCreate
    ) -> AccessRequestRead:
        if await self._users.get_by_entra_object_id(identity.entra_object_id) is not None:
            raise ConflictError("you already have an account")

        existing = await self._access_requests.find_latest_for_email(identity.email)
        if existing is not None and existing.status is AccessRequestStatus.PENDING:
            return existing

        request = await self._access_requests.create(
            email=identity.email,
            entra_object_id=identity.entra_object_id,
            name=identity.name,
            message=payload.message,
        )

        self._audit.add(
            AuditEntry(
                actor_email=identity.email,
                action=AuditAction.ACCESS_REQUEST_CREATED,
                resource_type="access_request",
                resource_id=str(request.id),
                after={"email": identity.email},
            )
        )
        return request

    async def list_pending(self) -> list[AccessRequestRead]:
        return await self._access_requests.list_by_status(AccessRequestStatus.PENDING)

    async def approve(
        self,
        *,
        actor: UserRead,
        actor_permissions: PermissionSet,
        request_id: uuid.UUID,
        payload: AccessRequestApproval,
    ) -> AccessRequestRead:
        request = await self._access_requests.get_by_id(request_id)
        if request is None:
            raise NotFoundError("access request does not exist")
        if request.status is not AccessRequestStatus.PENDING:
            raise ValidationError("access request has already been reviewed")

        role = await self._roles.get_by_id(payload.role_id)
        if role is None:
            raise NotFoundError("role does not exist")

        ensure_can_delegate(actor_permissions, role)

        user = await self._users.get_by_entra_object_id(request.entra_object_id)
        if user is None:
            user = await self._users.create(
                entra_object_id=request.entra_object_id,
                email=request.email,
                name=request.name,
            )

        await self._roles.grant(
            user_id=user.id,
            role_id=role.id,
            granted_by=actor.id,
            expires_at=payload.expires_at,
        )

        decided = await self._access_requests.record_decision(
            request_id=request_id,
            status=AccessRequestStatus.APPROVED,
            reviewed_by=actor.id,
            note=payload.note,
        )
        if decided is None:
            raise ValidationError("access request has already been reviewed")

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.ACCESS_REQUEST_APPROVED,
                resource_type="access_request",
                resource_id=str(request_id),
                after={"user_id": str(user.id), "role_key": role.key},
            )
        )
        return decided

    async def deny(
        self, *, actor: UserRead, request_id: uuid.UUID, payload: AccessRequestDenial
    ) -> AccessRequestRead:
        decided = await self._access_requests.record_decision(
            request_id=request_id,
            status=AccessRequestStatus.DENIED,
            reviewed_by=actor.id,
            note=payload.note,
        )
        if decided is None:
            raise NotFoundError("no pending access request with that id")

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.ACCESS_REQUEST_DENIED,
                resource_type="access_request",
                resource_id=str(request_id),
                after={"note": payload.note},
            )
        )
        return decided
