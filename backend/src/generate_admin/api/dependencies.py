from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Annotated

import asyncpg
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from generate_admin.core.cache import Cache as CacheProtocol
from generate_admin.core.config import Settings, get_settings
from generate_admin.core.errors import (
    AccountNotProvisionedError,
    AccountSuspendedError,
    PermissionDeniedError,
)
from generate_admin.core.security import TokenVerifier
from generate_admin.core.storage import S3Storage
from generate_admin.domain.access import PermissionSet, ResolvedAccess
from generate_admin.domain.enums import AccessState
from generate_admin.domain.permissions import Permission
from generate_admin.repositories import (
    AccessRequestRepository,
    AuditRepository,
    InvitationRepository,
    RoleRepository,
    UserRepository,
)
from generate_admin.schemas.session import Identity, Session
from generate_admin.schemas.user import UserRead
from generate_admin.services.access import AccessService
from generate_admin.services.access_request import AccessRequestService
from generate_admin.services.invitation import InvitationService
from generate_admin.services.member import MemberService

bearer_scheme = HTTPBearer(auto_error=True)

PROVISIONED_STATES = frozenset({AccessState.ACTIVE, AccessState.NO_ROLES})


@dataclass(frozen=True, slots=True)
class AuthContext:
    identity: Identity
    user: UserRead
    permissions: PermissionSet


async def get_connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    pool: asyncpg.Pool = request.app.state.pool
    async with pool.acquire() as connection, connection.transaction():
        yield connection


def get_read_cache(request: Request) -> CacheProtocol:
    return request.app.state.cache


def get_storage(request: Request) -> S3Storage:
    return request.app.state.storage


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


Connection = Annotated[asyncpg.Connection, Depends(get_connection)]
Cache = Annotated[CacheProtocol, Depends(get_read_cache)]
Storage = Annotated[S3Storage, Depends(get_storage)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_user_repository(connection: Connection) -> UserRepository:
    return UserRepository(connection)


def get_role_repository(connection: Connection) -> RoleRepository:
    return RoleRepository(connection)


def get_invitation_repository(connection: Connection) -> InvitationRepository:
    return InvitationRepository(connection)


def get_access_request_repository(connection: Connection) -> AccessRequestRepository:
    return AccessRequestRepository(connection)


def get_audit_repository(connection: Connection) -> AuditRepository:
    return AuditRepository(connection)


Users = Annotated[UserRepository, Depends(get_user_repository)]
Roles = Annotated[RoleRepository, Depends(get_role_repository)]
Invitations = Annotated[InvitationRepository, Depends(get_invitation_repository)]
AccessRequests = Annotated[AccessRequestRepository, Depends(get_access_request_repository)]
Audit = Annotated[AuditRepository, Depends(get_audit_repository)]


def get_access_service(
    users: Users,
    invitations: Invitations,
    access_requests: AccessRequests,
    roles: Roles,
    audit: Audit,
) -> AccessService:
    return AccessService(
        users=users,
        invitations=invitations,
        access_requests=access_requests,
        roles=roles,
        audit=audit,
    )


def get_member_service(users: Users, roles: Roles, audit: Audit) -> MemberService:
    return MemberService(users=users, roles=roles, audit=audit)


def get_invitation_service(
    invitations: Invitations, roles: Roles, users: Users, audit: Audit, settings: AppSettings
) -> InvitationService:
    return InvitationService(
        invitations=invitations,
        roles=roles,
        users=users,
        audit=audit,
        default_ttl_hours=settings.invitation_ttl_hours,
    )


def get_access_request_service(
    access_requests: AccessRequests, users: Users, roles: Roles, audit: Audit
) -> AccessRequestService:
    return AccessRequestService(
        access_requests=access_requests, users=users, roles=roles, audit=audit
    )


AccessServiceDep = Annotated[AccessService, Depends(get_access_service)]
MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]
InvitationServiceDep = Annotated[InvitationService, Depends(get_invitation_service)]
AccessRequestServiceDep = Annotated[AccessRequestService, Depends(get_access_request_service)]


async def get_identity(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> Identity:
    return await verifier.verify(credentials.credentials)


CurrentIdentity = Annotated[Identity, Depends(get_identity)]


async def get_resolved_access(
    identity: CurrentIdentity, access: AccessServiceDep
) -> ResolvedAccess:
    return await access.resolve(identity)


ResolvedAccessDep = Annotated[ResolvedAccess, Depends(get_resolved_access)]


def get_session(resolved: ResolvedAccessDep) -> Session:
    return resolved.session


CurrentSession = Annotated[Session, Depends(get_session)]


def get_auth_context(resolved: ResolvedAccessDep) -> AuthContext:
    session = resolved.session

    if session.access_state is AccessState.SUSPENDED:
        raise AccountSuspendedError("your account has been suspended")

    if session.access_state not in PROVISIONED_STATES or session.user is None:
        raise AccountNotProvisionedError(
            "your account does not have access to this workspace",
            details={"access_state": session.access_state.value},
        )

    return AuthContext(
        identity=session.identity,
        user=session.user,
        permissions=resolved.permissions,
    )


CurrentUser = Annotated[AuthContext, Depends(get_auth_context)]


def require(*permissions: Permission) -> Callable[..., AuthContext]:
    def dependency(context: CurrentUser) -> AuthContext:
        missing = [item for item in permissions if not context.permissions.allows(item)]
        if missing:
            raise PermissionDeniedError(
                "you do not have permission to perform this action",
                details={"missing": [item.value for item in missing]},
            )
        return context

    return dependency
