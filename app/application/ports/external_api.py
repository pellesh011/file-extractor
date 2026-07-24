from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class FileNamesResult:
    file_names: list[str]


class ExternalAPIClient(ABC):
    @abstractmethod
    async def get_file_names(self, candidate_id: str | None = None) -> FileNamesResult: ...

    @abstractmethod
    async def download_files_stream(self, file_names: list[str]) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def mark_downloaded(
        self, file_names: list[str], candidate_id: str | None = None
    ) -> tuple[int, int]: ...
