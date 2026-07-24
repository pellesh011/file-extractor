from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GetTaskStatusQuery:
    task_id: str


@dataclass
class TaskStatusResult:
    task_id: str
    status: str
    received_files: int
    processed_files: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
