from fastapi import APIRouter, Depends

from app.application.commands import StartDownloadCommand
from app.application.handlers import StartDownloadHandler
from app.application.handlers.statistics_handler import StatisticsHandler
from app.application.queries.get_statistics import GetStatisticsQuery
from app.application.unit_of_work import UnitOfWork
from app.domain.repositories.file_repository import FileFilters
from app.presentation.api.deps import get_start_download_handler, get_statistics_handler, get_uow
from app.presentation.schemas.requests import StartDownloadRequest
from app.presentation.schemas.responses import (
    DownloadTaskResponse,
    StatisticsResponse,
    TaskCreatedResponse,
)

router = APIRouter()


@router.post("/api/download/start", response_model=TaskCreatedResponse)
async def start_download(
    body: StartDownloadRequest,
    handler: StartDownloadHandler = Depends(get_start_download_handler),
) -> TaskCreatedResponse:
    command = StartDownloadCommand(candidate_id=body.candidate_id)
    task_id = await handler.execute(command)
    return TaskCreatedResponse(task_id=task_id)


@router.get("/api/download/{task_id}", response_model=DownloadTaskResponse)
async def get_task_status(
    task_id: str,
    uow: UnitOfWork = Depends(get_uow),
) -> DownloadTaskResponse:
    async with uow:
        task = await uow.task_repo.get_by_id(task_id)
    if not task:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Task not found")
    return DownloadTaskResponse(
        task_id=task.id,
        status=task.status.name,
        received_files=task.received_files,
        processed_files=task.processed_files,
        error=task.error,
        started_at=task.started_at,
        finished_at=task.finished_at,
    )


@router.get("/api/files")
async def get_files(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, object]:
    async with uow:
        result = await uow.file_repo.list(
            filters=FileFilters(status=status),
            page=page,
            per_page=per_page,
        )
    return {
        "items": [
            {
                "id": str(f.id),
                "filename": f.filename,
                "size": f.size.value,
                "status": f.status.name,
                "hash": str(f.hash) if f.hash else None,
                "created_at": f.created_at.isoformat(),
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
            }
            for f in result.items
        ],
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
    }


@router.post("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(
    handler: StatisticsHandler = Depends(get_statistics_handler),
) -> StatisticsResponse:
    query = GetStatisticsQuery()
    result = await handler.execute(query)
    return StatisticsResponse(
        total_files=result.total_files,
        total_size=result.total_size,
        uploaded_files=result.uploaded_files,
        failed_files=result.failed_files,
        average_file_size=result.average_file_size,
    )
