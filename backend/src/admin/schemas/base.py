import base64
from typing import Any, Self

import asyncpg
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic import ValidationError as PydanticError

from admin.core.errors import ValidationError


class RequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ReadDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True, populate_by_name=True)

    @classmethod
    def from_row(cls, row: asyncpg.Record) -> Self:
        return cls.model_validate(dict(row))

    @classmethod
    def from_rows(cls, rows: list[asyncpg.Record]) -> list[Self]:
        return [cls.from_row(row) for row in rows]

    @classmethod
    def from_optional_row(cls, row: asyncpg.Record | None) -> Self | None:
        return None if row is None else cls.from_row(row)


CURSOR_ADAPTER = TypeAdapter(list[str])


def encode_cursor(values: list[Any]) -> str:
    payload = CURSOR_ADAPTER.dump_json([str(value) for value in values])
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> list[str] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        return CURSOR_ADAPTER.validate_json(base64.urlsafe_b64decode(padded))
    except (ValueError, PydanticError) as error:
        raise ValidationError("cursor is malformed") from error


class CursorParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None

    @property
    def fetch_limit(self) -> int:
        return self.limit + 1

    def decoded(self) -> list[str] | None:
        return decode_cursor(self.cursor)


class CursorPage[ItemT](BaseModel):
    items: list[ItemT]
    next_cursor: str | None = None
    has_more: bool = False
    limit: int

    @classmethod
    def build(
        cls,
        rows: list[Any],
        params: CursorParams,
        cursor_of: Any,
    ) -> "CursorPage[ItemT]":
        has_more = len(rows) > params.limit
        page = rows[: params.limit]
        return cls(
            items=page,
            has_more=has_more,
            next_cursor=encode_cursor(cursor_of(page[-1])) if has_more and page else None,
            limit=params.limit,
        )
