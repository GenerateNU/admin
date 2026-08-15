from dataclasses import dataclass
from enum import StrEnum


class Permission(StrEnum):
    MEMBERS_READ = "core.members.read"
    MEMBERS_INVITE = "core.members.invite"
    MEMBERS_SUSPEND = "core.members.suspend"
    ROLES_READ = "core.roles.read"
    ROLES_GRANT = "core.roles.grant"
    ROLES_REVOKE = "core.roles.revoke"
    ACCESS_REQUESTS_READ = "core.access_requests.read"
    ACCESS_REQUESTS_REVIEW = "core.access_requests.review"
    AUDIT_READ = "core.audit.read"
    MEDIA_READ = "core.media.read"
    MEDIA_DELETE = "core.media.delete"

    @property
    def description(self) -> str:
        return PERMISSION_DESCRIPTIONS[self]


PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.MEMBERS_READ: "View the member directory",
    Permission.MEMBERS_INVITE: "Invite people to the workspace",
    Permission.MEMBERS_SUSPEND: "Suspend and reinstate member accounts",
    Permission.ROLES_READ: "View roles and their permissions",
    Permission.ROLES_GRANT: "Grant roles to members",
    Permission.ROLES_REVOKE: "Revoke roles from members",
    Permission.ACCESS_REQUESTS_READ: "View pending access requests",
    Permission.ACCESS_REQUESTS_REVIEW: "Approve or deny access requests",
    Permission.AUDIT_READ: "Read the audit log",
    Permission.MEDIA_READ: "View private files uploaded by other members",
    Permission.MEDIA_DELETE: "Delete files uploaded by other members",
}


class SystemRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    key: SystemRole
    name: str
    permissions: frozenset[Permission]


ROLE_DEFINITIONS: tuple[RoleDefinition, ...] = (
    RoleDefinition(
        key=SystemRole.OWNER,
        name="Owner",
        permissions=frozenset(Permission),
    ),
    RoleDefinition(
        key=SystemRole.ADMIN,
        name="Admin",
        permissions=frozenset(Permission) - {Permission.ROLES_GRANT, Permission.ROLES_REVOKE},
    ),
)

ROLE_DEFINITIONS_BY_KEY: dict[SystemRole, RoleDefinition] = {
    definition.key: definition for definition in ROLE_DEFINITIONS
}
