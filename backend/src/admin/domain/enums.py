from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class AccessState(StrEnum):
    NO_ACCESS = "no_access"
    INVITED = "invited"
    PENDING = "pending"
    DENIED = "denied"
    ACTIVE = "active"
    NO_ROLES = "no_roles"
    SUSPENDED = "suspended"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AccessRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class MediaPurpose(StrEnum):
    AVATAR = "avatar"


class AuditAction(StrEnum):
    USER_PROVISIONED = "user.provisioned"
    USER_SUSPENDED = "user.suspended"
    USER_REINSTATED = "user.reinstated"
    ROLE_GRANTED = "role.granted"
    ROLE_REVOKED = "role.revoked"
    INVITATION_CREATED = "invitation.created"
    INVITATION_ACCEPTED = "invitation.accepted"
    INVITATION_REVOKED = "invitation.revoked"
    ACCESS_REQUEST_CREATED = "access_request.created"
    ACCESS_REQUEST_APPROVED = "access_request.approved"
    ACCESS_REQUEST_DENIED = "access_request.denied"
    MEDIA_UPLOADED = "media.uploaded"
    MEDIA_DELETED = "media.deleted"
