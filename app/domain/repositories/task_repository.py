from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.download_task import DownloadTask


class TaskRepository(ABC):
    @abstractmethod
    async def add(self, task: DownloadTask) -> None: ...

    @abstractmethod
    async def get_by_id(self, task_id: str) -> DownloadTask | None: ...

    @abstractmethod
    async def update(self, task: DownloadTask) -> None: ...

    @abstractmethod
    async def list(self, limit: int = 20, offset: int = 0) -> list[DownloadTask]: ...
