from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.download_task import DownloadTask
from app.domain.entities.file import File
from app.domain.repositories import FileRepository as FileRepositoryInterface
from app.domain.repositories import PaginatedFiles
from app.domain.repositories.file_repository import FileFilters as FileDomainFilters
from app.domain.repositories.task_repository import TaskRepository as TaskRepositoryInterface
from app.domain.value_objects import FileHash, FileId, FileSize, FileStatus, StorageKey
from app.infrastructure.database.models import DownloadedFileModel, DownloadTaskModel, FileModel


class SQLAlchemyFileRepository(FileRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, file: File) -> None:
        model = self._to_model(file)
        self._session.add(model)

    async def get_by_id(self, file_id: FileId) -> File | None:
        model = await self._session.get(FileModel, file_id.value)
        return self._to_domain(model) if model else None

    async def get_by_storage_key(self, storage_key: str) -> File | None:
        result = await self._session.execute(
            select(FileModel).where(FileModel.storage_key == storage_key)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list(
        self,
        filters: FileDomainFilters | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedFiles:
        query = select(FileModel)
        count_query = select(func.count()).select_from(FileModel)

        if filters:
            if filters.status:
                query = query.where(FileModel.status == filters.status)
                count_query = count_query.where(FileModel.status == filters.status)
            if filters.filename_contains:
                query = query.where(FileModel.filename.contains(filters.filename_contains))
                count_query = count_query.where(
                    FileModel.filename.contains(filters.filename_contains)
                )

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * per_page
        query = query.order_by(FileModel.created_at.desc()).offset(offset).limit(per_page)
        result = await self._session.execute(query)
        models = result.scalars().all()

        return PaginatedFiles(
            items=[self._to_domain(m) for m in models],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def delete(self, file_id: FileId) -> None:
        model = await self._session.get(FileModel, file_id.value)
        if model:
            await self._session.delete(model)

    async def count_by_status(self, status: str) -> int:
        query = select(func.count()).select_from(FileModel)
        if status:
            query = query.where(FileModel.status == status)
        result = await self._session.execute(query)
        return result.scalar_one()

    @staticmethod
    def _to_model(file: File) -> FileModel:
        return FileModel(
            id=file.id.value,
            filename=file.filename,
            size=file.size.value,
            hash=str(file.hash) if file.hash else None,
            storage_key=str(file.storage_key) if file.storage_key else None,
            status=file.status.name,
            created_at=file.created_at,
            uploaded_at=file.uploaded_at,
        )

    @staticmethod
    def _to_domain(model: FileModel) -> File:
        return File(
            file_id=FileId(str(model.id)),
            filename=model.filename,
            size=FileSize(model.size),
            hash=FileHash(model.hash) if model.hash else None,
            storage_key=StorageKey(model.storage_key) if model.storage_key else None,
            status=FileStatus[model.status],
            created_at=model.created_at,
            uploaded_at=model.uploaded_at,
        )


class SQLAlchemyTaskRepository(TaskRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: DownloadTask) -> None:
        model = self._to_model(task)
        self._session.add(model)

    async def get_by_id(self, task_id: str) -> DownloadTask | None:
        model = await self._session.get(DownloadTaskModel, task_id)
        return self._to_domain(model) if model else None

    async def update(self, task: DownloadTask) -> None:
        model = await self._session.get(DownloadTaskModel, task.id)
        if not model:
            return
        model.status = task.status.name
        model.received_files = task.received_files
        model.processed_files = task.processed_files
        model.error = task.error
        model.started_at = task.started_at
        model.finished_at = task.finished_at
        model.worker_id = task.worker_id
        model.last_heartbeat = task.last_heartbeat
        model.attempts = task.attempts
        model.blocked_until = task.blocked_until
        model.block_reason = task.block_reason

    async def list_tasks(self, limit: int = 20, offset: int = 0) -> list[DownloadTask]:
        result = await self._session.execute(
            select(DownloadTaskModel)
            .order_by(DownloadTaskModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def claim(self, task_id: str, worker_id: str) -> DownloadTask | None:
        now = datetime.now(UTC)
        stmt = (
            update(DownloadTaskModel)
            .where(
                DownloadTaskModel.id == task_id,
                DownloadTaskModel.status == "PENDING",
            )
            .values(
                status="RUNNING",
                worker_id=worker_id,
                started_at=now,
                last_heartbeat=now,
                attempts=DownloadTaskModel.attempts + 1,
                error=None,
                blocked_until=None,
                block_reason=None,
            )
            .returning(DownloadTaskModel)
        )
        result = await self._session.execute(stmt)
        row = result.fetchone()
        if row is None:
            return None
        return self._to_domain(row[0])

    async def update_heartbeat(self, task_id: str) -> None:
        now = datetime.now(UTC)
        await self._session.execute(
            update(DownloadTaskModel)
            .where(
                DownloadTaskModel.id == task_id,
                DownloadTaskModel.status == "RUNNING",
            )
            .values(last_heartbeat=now)
        )

    async def reclaim_stuck(
        self, max_heartbeat_age: timedelta, limit: int = 10
    ) -> list[DownloadTask]:
        cutoff = datetime.now(UTC) - max_heartbeat_age
        subq = (
            select(DownloadTaskModel.id)
            .where(
                DownloadTaskModel.status == "RUNNING",
                DownloadTaskModel.last_heartbeat < cutoff,
            )
            .limit(limit)
            .subquery()
        )
        result = await self._session.execute(
            update(DownloadTaskModel)
            .where(DownloadTaskModel.id.in_(select(subq.c.id)))
            .values(
                status="PENDING",
                worker_id=None,
                last_heartbeat=None,
                blocked_until=None,
                block_reason=None,
            )
            .returning(DownloadTaskModel)
        )
        return [self._to_domain(row[0]) for row in result.fetchall()]

    async def reclaim_blocked(self, limit: int = 10) -> list[DownloadTask]:
        now = datetime.now(UTC)
        subq = (
            select(DownloadTaskModel.id)
            .where(
                DownloadTaskModel.status == "BLOCKED",
                DownloadTaskModel.blocked_until < now,
            )
            .limit(limit)
            .subquery()
        )
        result = await self._session.execute(
            update(DownloadTaskModel)
            .where(DownloadTaskModel.id.in_(select(subq.c.id)))
            .values(
                status="PENDING",
                worker_id=None,
                blocked_until=None,
                block_reason=None,
            )
            .returning(DownloadTaskModel)
        )
        return [self._to_domain(row[0]) for row in result.fetchall()]

    async def downloaded_file_exists(self, task_id: str, filename: str) -> bool:
        result = await self._session.execute(
            select(DownloadedFileModel).where(
                DownloadedFileModel.task_id == task_id,
                DownloadedFileModel.file_name == filename,
            )
        )
        return result.scalar_one_or_none() is not None

    async def record_downloaded_file(
        self, task_id: str, filename: str, file_hash: FileHash
    ) -> None:
        self._session.add(
            DownloadedFileModel(
                task_id=task_id,
                file_name=filename,
                hash=str(file_hash),
            )
        )

    async def delete_downloaded_file(self, task_id: str, filename: str) -> None:
        await self._session.execute(
            delete(DownloadedFileModel).where(
                DownloadedFileModel.task_id == task_id,
                DownloadedFileModel.file_name == filename,
            )
        )

    @staticmethod
    def _to_model(task: DownloadTask) -> DownloadTaskModel:
        return DownloadTaskModel(
            id=task.id,
            candidate_id=task.candidate_id,
            status=task.status.name,
            received_files=task.received_files,
            processed_files=task.processed_files,
            error=task.error,
            started_at=task.started_at,
            finished_at=task.finished_at,
            worker_id=task.worker_id,
            last_heartbeat=task.last_heartbeat,
            attempts=task.attempts,
            blocked_until=task.blocked_until,
            block_reason=task.block_reason,
        )

    @staticmethod
    def _to_domain(model: DownloadTaskModel) -> DownloadTask:
        from app.domain.value_objects.statuses import TaskStatus

        return DownloadTask(
            task_id=model.id,
            candidate_id=model.candidate_id,
            status=TaskStatus[model.status],
            received_files=model.received_files,
            processed_files=model.processed_files,
            error=model.error,
            started_at=model.started_at,
            finished_at=model.finished_at,
            worker_id=model.worker_id,
            last_heartbeat=model.last_heartbeat,
            attempts=model.attempts,
            blocked_until=model.blocked_until,
            block_reason=model.block_reason,
        )
