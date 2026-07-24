from __future__ import annotations

from datetime import UTC, datetime

from app.domain.exceptions import InvalidStatusTransitionError, TaskNotRunningError
from app.domain.value_objects import TaskStatus


class DownloadTask:
    def __init__(
        self,
        task_id: str,
        candidate_id: str,
        status: TaskStatus = TaskStatus.CREATED,
        received_files: int = 0,
        processed_files: int = 0,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        self._id = task_id
        self._candidate_id = candidate_id
        self._status = status
        self._received_files = received_files
        self._processed_files = processed_files
        self._error = error
        self._started_at = started_at
        self._finished_at = finished_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def received_files(self) -> int:
        return self._received_files

    @property
    def processed_files(self) -> int:
        return self._processed_files

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def finished_at(self) -> datetime | None:
        return self._finished_at

    def start(self) -> None:
        if self._status != TaskStatus.CREATED:
            raise InvalidStatusTransitionError(
                "DownloadTask", self._status.name, TaskStatus.RUNNING.name
            )
        self._status = TaskStatus.RUNNING
        self._started_at = datetime.now(UTC)

    def increase_received(self, count: int) -> None:
        if self._status != TaskStatus.RUNNING:
            raise TaskNotRunningError(self._id, self._status.name)
        self._received_files += count

    def increase_processed(self, count: int) -> None:
        if self._status != TaskStatus.RUNNING:
            raise TaskNotRunningError(self._id, self._status.name)
        self._processed_files += count

    def complete(self) -> None:
        if self._status != TaskStatus.RUNNING:
            raise InvalidStatusTransitionError(
                "DownloadTask", self._status.name, TaskStatus.COMPLETED.name
            )
        self._status = TaskStatus.COMPLETED
        self._finished_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        if self._status not in (TaskStatus.CREATED, TaskStatus.RUNNING):
            raise InvalidStatusTransitionError(
                "DownloadTask", self._status.name, TaskStatus.FAILED.name
            )
        self._status = TaskStatus.FAILED
        self._error = error
        self._finished_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return (
            f"DownloadTask(id={self._id}, status={self._status.name}, "
            f"received={self._received_files}, processed={self._processed_files})"
        )
