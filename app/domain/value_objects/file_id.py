from __future__ import annotations

from uuid import UUID, uuid4


class FileId:
    def __init__(self, value: str | UUID | None = None) -> None:
        if value is None:
            self._value = uuid4()
        elif isinstance(value, UUID):
            self._value = value
        else:
            self._value = UUID(value)

    @property
    def value(self) -> UUID:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"FileId({self._value})"
