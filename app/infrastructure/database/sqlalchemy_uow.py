from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.unit_of_work import UnitOfWork
from app.infrastructure.database.repositories import (
    SQLAlchemyFileRepository,
    SQLAlchemyTaskRepository,
)


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._file_repo = SQLAlchemyFileRepository(session)
        self._task_repo = SQLAlchemyTaskRepository(session)

    @property
    def file_repo(self) -> SQLAlchemyFileRepository:
        return self._file_repo

    @property
    def task_repo(self) -> SQLAlchemyTaskRepository:
        return self._task_repo

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        if args[0] is not None:
            await self.rollback()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()
