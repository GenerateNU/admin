from typing import Any

import asyncpg


class Repository:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self.connection = connection


class ConditionSet:
    def __init__(self, *, start_index: int = 1) -> None:
        self._clauses: list[str] = []
        self._params: list[Any] = []
        self._start_index = start_index

    def add(self, template: str, *values: Any) -> None:
        placeholders = tuple(
            f"${self._start_index + len(self._params) + offset}" for offset in range(len(values))
        )
        self._clauses.append(template.format(*placeholders))
        self._params.extend(values)

    def add_if(self, condition: bool, template: str, *values: Any) -> None:
        if condition:
            self.add(template, *values)

    @property
    def where(self) -> str:
        return f"WHERE {' AND '.join(self._clauses)}" if self._clauses else ""

    @property
    def params(self) -> list[Any]:
        return list(self._params)

    @property
    def next_index(self) -> int:
        return self._start_index + len(self._params)
