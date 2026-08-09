from http import HTTPStatus


class DomainError(Exception):
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class ValidationError(DomainError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "validation_failed"


class AuthenticationError(DomainError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthenticated"


class PermissionDeniedError(DomainError):
    status_code = HTTPStatus.FORBIDDEN
    code = "permission_denied"


class AccountNotProvisionedError(DomainError):
    status_code = HTTPStatus.FORBIDDEN
    code = "account_not_provisioned"


class AccountSuspendedError(DomainError):
    status_code = HTTPStatus.FORBIDDEN
    code = "account_suspended"


class PrivilegeEscalationError(DomainError):
    status_code = HTTPStatus.FORBIDDEN
    code = "privilege_escalation"


class LastOwnerError(DomainError):
    status_code = HTTPStatus.CONFLICT
    code = "last_owner"
