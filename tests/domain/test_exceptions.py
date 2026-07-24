from app.core.exceptions import AppError
from app.domain.exceptions import (
    InvalidFileHashError,
    InvalidStatusTransitionError,
    NegativeFileSizeError,
    TaskAlreadyCompletedError,
    TaskNotRunningError,
)


class TestDomainExceptions:
    def test_invalid_status_transition(self) -> None:
        exc = InvalidStatusTransitionError("File", "CREATED", "FAILED")
        assert isinstance(exc, AppError)
        assert "File" in str(exc)
        assert exc.entity == "File"

    def test_invalid_file_hash(self) -> None:
        exc = InvalidFileHashError("bad")
        assert isinstance(exc, AppError)
        assert exc.value == "bad"

    def test_negative_file_size(self) -> None:
        exc = NegativeFileSizeError(-5)
        assert isinstance(exc, AppError)
        assert exc.value == -5

    def test_task_already_completed(self) -> None:
        exc = TaskAlreadyCompletedError("task-1")
        assert isinstance(exc, AppError)
        assert exc.task_id == "task-1"

    def test_task_not_running(self) -> None:
        exc = TaskNotRunningError("task-1", "CREATED")
        assert isinstance(exc, AppError)
        assert exc.task_id == "task-1"
        assert exc.status == "CREATED"
