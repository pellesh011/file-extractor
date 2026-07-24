from __future__ import annotations

import hashlib
import re

from app.domain.exceptions import InvalidFileHashError

SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class FileHash:
    def __init__(self, value: str) -> None:
        if not SHA256_HEX_PATTERN.match(value):
            raise InvalidFileHashError(value)
        self._value = value

    @classmethod
    def compute(cls, data: bytes) -> FileHash:
        return cls(hashlib.sha256(data).hexdigest())

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileHash):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"FileHash({self._value})"
