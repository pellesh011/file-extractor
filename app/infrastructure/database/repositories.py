from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.download_task import DownloadTask
from app.domain.entities.file import File
from app.domain.repositories import FileRepository as FileRepositoryInterface
from app.domain.repositories import PaginatedFiles
from app.domain.repositories.file_repository import FileFilters as FileDomainFilters
from app.domain.repositories.task_repository import TaskRepository as TaskRepositoryInterface
from app.domain.value_objects import FileHash, FileId, FileSize, FileStatus, StorageKey
from app.infrastructure.database.models import DownloadTaskModel, FileModel


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

    async def list(self, limit: int = 20, offset: int = 0) -> list[DownloadTask]:
        result = await self._session.execute(
            select(DownloadTaskModel)
            .order_by(DownloadTaskModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

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
        )
