from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ExtractedFile:
    filename: str
    content: bytes
    size: int


class FileProcessor(ABC):
    @abstractmethod
    async def extract_stream(
        self, zip_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[ExtractedFile]: ...
