from enum import StrEnum


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
