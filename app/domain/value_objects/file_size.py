from __future__ import annotations

from app.domain.exceptions import NegativeFileSizeError


class FileSize:
    def __init__(self, value: int) -> None:
        if value < 0:
            raise NegativeFileSizeError(value)
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileSize):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"FileSize({self._value})"
