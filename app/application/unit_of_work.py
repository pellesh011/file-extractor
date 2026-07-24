from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.repositories import FileRepository, TaskRepository


class UnitOfWork(ABC):
    @property
    @abstractmethod
    def file_repo(self) -> FileRepository: ...

    @property
    @abstractmethod
    def task_repo(self) -> TaskRepository: ...

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork: ...

    @abstractmethod
    async def __aexit__(self, *args: object) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...
