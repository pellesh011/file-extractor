from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities.file import File
from app.domain.value_objects import FileId


@dataclass
class FileFilters:
    status: str | None = None
    filename_contains: str | None = None


@dataclass
class PaginatedFiles:
    items: list[File]
    total: int
    page: int
    per_page: int


class FileRepository(ABC):
    @abstractmethod
    async def add(self, file: File) -> None: ...

    @abstractmethod
    async def get_by_id(self, file_id: FileId) -> File | None: ...

    @abstractmethod
    async def get_by_storage_key(self, storage_key: str) -> File | None: ...

    @abstractmethod
    async def list(
        self, filters: FileFilters | None = None, page: int = 1, per_page: int = 20
    ) -> PaginatedFiles: ...

    @abstractmethod
    async def count_by_status(self, status: str) -> int: ...
