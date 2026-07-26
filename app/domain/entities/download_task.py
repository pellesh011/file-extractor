from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.exceptions import InvalidStatusTransitionError, TaskNotRunningError
from app.domain.value_objects import TaskStatus


class DownloadTask:
    def __init__(
        self,
        task_id: str,
        candidate_id: str,
        status: TaskStatus = TaskStatus.PENDING,
        received_files: int = 0,
        processed_files: int = 0,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        worker_id: str | None = None,
        last_heartbeat: datetime | None = None,
        attempts: int = 0,
        blocked_until: datetime | None = None,
        block_reason: str | None = None,
    ) -> None:
        self._id = task_id
        self._candidate_id = candidate_id
        self._status = status
        self._received_files = received_files
        self._processed_files = processed_files
        self._error = error
        self._started_at = started_at
        self._finished_at = finished_at
        self._worker_id = worker_id
        self._last_heartbeat = last_heartbeat
        self._attempts = attempts
        self._blocked_until = blocked_until
        self._block_reason = block_reason

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

    @property
    def worker_id(self) -> str | None:
        return self._worker_id

    @property
    def last_heartbeat(self) -> datetime | None:
        return self._last_heartbeat

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def blocked_until(self) -> datetime | None:
        return self._blocked_until

    @property
    def block_reason(self) -> str | None:
        return self._block_reason

    def claim(self, worker_id: str) -> None:
        if self._status != TaskStatus.PENDING:
            raise InvalidStatusTransitionError(
                "DownloadTask", self._status.name, TaskStatus.RUNNING.name
            )
        self._status = TaskStatus.RUNNING
        self._worker_id = worker_id
        self._started_at = datetime.now(UTC)
        self._last_heartbeat = datetime.now(UTC)
        self._attempts += 1

    def heartbeat(self) -> None:
        if self._status != TaskStatus.RUNNING:
            raise TaskNotRunningError(self._id, self._status.name)
        self._last_heartbeat = datetime.now(UTC)

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
                "DownloadTask", self._status.name, TaskStatus.SUCCESS.name
            )
        self._status = TaskStatus.SUCCESS
        self._finished_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        if self._status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            raise InvalidStatusTransitionError(
                "DownloadTask", self._status.name, TaskStatus.FAILED.name
            )
        self._status = TaskStatus.FAILED
        self._error = error
        self._finished_at = datetime.now(UTC)

    def block(self, retry_after_seconds: int, reason: str = "") -> None:
        if self._status != TaskStatus.RUNNING:
            raise TaskNotRunningError(self._id, self._status.name)
        self._status = TaskStatus.BLOCKED
        self._blocked_until = datetime.now(UTC) + timedelta(seconds=retry_after_seconds)
        self._block_reason = reason
        self._error = f"External API block: {reason}" if reason else "External API block"

    def is_blocked(self) -> bool:
        return self._status == TaskStatus.BLOCKED and (
            self._blocked_until is None or self._blocked_until > datetime.now(UTC)
        )

    def __repr__(self) -> str:
        return (
            f"DownloadTask(id={self._id}, status={self._status.name}, "
            f"received={self._received_files}, processed={self._processed_files}, "
            f"attempts={self._attempts})"
        )
