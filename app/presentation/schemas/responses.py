from datetime import datetime

from pydantic import BaseModel


class DownloadTaskResponse(BaseModel):
    task_id: str
    status: str
    received_files: int = 0
    processed_files: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskCreatedResponse(BaseModel):
    task_id: str


class FileItemResponse(BaseModel):
    id: str
    filename: str
    size: int
    status: str
    hash: str | None = None
    created_at: datetime
    uploaded_at: datetime | None = None


class PaginatedFilesResponse(BaseModel):
    items: list[FileItemResponse]
    total: int
    page: int
    per_page: int


class StatisticsResponse(BaseModel):
    total_files: int = 0
    total_size: int = 0
    uploaded_files: int = 0
    failed_files: int = 0
    average_file_size: float = 0.0


class ErrorResponse(BaseModel):
    detail: str
