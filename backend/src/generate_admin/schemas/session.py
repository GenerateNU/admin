import uuid

from pydantic import EmailStr, Field

from generate_admin.domain.enums import AccessState
from generate_admin.schemas.base import ReadDTO
from generate_admin.schemas.user import UserRead


class Identity(ReadDTO):
    entra_object_id: uuid.UUID
    email: EmailStr
    name: str


class Session(ReadDTO):
    access_state: AccessState
    identity: Identity
    user: UserRead | None = None
    permissions: list[str] = Field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.access_state is AccessState.ACTIVE
