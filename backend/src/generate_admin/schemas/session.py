import uuid

from pydantic import EmailStr

from generate_admin.schemas.base import ReadDTO


class Identity(ReadDTO):
    """Who the caller is, straight from a verified Entra token."""

    entra_object_id: uuid.UUID
    email: EmailStr
    name: str
