from dataclasses import dataclass, field

from admin.schemas.audit import AuditEntry


@dataclass(slots=True)
class AuditLog:
    entries: list[AuditEntry] = field(default_factory=list)

    def add(self, *entries: AuditEntry) -> None:
        self.entries.extend(entries)
