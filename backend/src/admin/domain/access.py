from dataclasses import dataclass

from admin.domain.permissions import Permission
from admin.schemas.session import Session


@dataclass(frozen=True, slots=True)
class PermissionSet:
    granted: frozenset[str]

    @classmethod
    def from_keys(cls, keys: list[str]) -> "PermissionSet":
        return cls(granted=frozenset(keys))

    def allows(self, permission: Permission) -> bool:
        return permission.value in self.granted

    def allows_all(self, permissions: set[Permission]) -> bool:
        return all(self.allows(permission) for permission in permissions)

    @property
    def keys(self) -> list[str]:
        return sorted(self.granted)

    @property
    def is_empty(self) -> bool:
        return not self.granted


@dataclass(frozen=True, slots=True)
class ResolvedAccess:
    session: Session
    permissions: PermissionSet
