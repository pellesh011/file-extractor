from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta

from app.domain.entities.download_task import DownloadTask
from app.domain.value_objects import FileHash


class TaskRepository(ABC):
    @abstractmethod
    async def add(self, task: DownloadTask) -> None: ...

    @abstractmethod
    async def get_by_id(self, task_id: str) -> DownloadTask | None: ...

    @abstractmethod
    async def update(self, task: DownloadTask) -> None: ...

    @abstractmethod
    async def list_tasks(self, limit: int = 20, offset: int = 0) -> list[DownloadTask]: ...

    @abstractmethod
    async def claim(self, task_id: str, worker_id: str) -> DownloadTask | None:
        """Atomically claim a PENDING task. Returns the task or None."""

    @abstractmethod
    async def update_heartbeat(self, task_id: str) -> None:
        """Update last_heartbeat for a RUNNING task."""

    @abstractmethod
    async def reclaim_stuck(
        self, max_heartbeat_age: timedelta, limit: int = 10
    ) -> list[DownloadTask]:
        """Reset RUNNING tasks with stale heartbeat back to PENDING."""

    @abstractmethod
    async def reclaim_blocked(self, limit: int = 10) -> list[DownloadTask]:
        """Reset BLOCKED tasks past their blocked_until back to PENDING."""

    @abstractmethod
    async def downloaded_file_exists(self, task_id: str, filename: str) -> bool: ...

    @abstractmethod
    async def record_downloaded_file(
        self, task_id: str, filename: str, file_hash: FileHash
    ) -> None: ...
