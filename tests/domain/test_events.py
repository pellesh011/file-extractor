from datetime import UTC, datetime

from app.domain.events.file_uploaded import FileUploadedEvent
from app.domain.events.task_completed import TaskCompletedEvent


class TestFileUploadedEvent:
    def test_creation(self) -> None:
        event = FileUploadedEvent(
            file_id="file-1",
            storage_key="files/hash.txt",
            filename="test.txt",
            size=100,
        )
        assert event.file_id == "file-1"
        assert event.storage_key == "files/hash.txt"
        assert event.filename == "test.txt"
        assert event.size == 100
        assert isinstance(event.timestamp, datetime)

    def test_default_timestamp_is_utc(self) -> None:
        event = FileUploadedEvent(file_id="f1", storage_key="k", filename="n", size=1)
        assert event.timestamp.tzinfo == UTC


class TestTaskCompletedEvent:
    def test_creation(self) -> None:
        event = TaskCompletedEvent(
            task_id="task-1",
            status="COMPLETED",
            file_count=5,
            duration_seconds=12.3,
        )
        assert event.task_id == "task-1"
        assert event.status == "COMPLETED"
        assert event.file_count == 5
        assert event.duration_seconds == 12.3
        assert isinstance(event.timestamp, datetime)

    def test_default_duration_none(self) -> None:
        event = TaskCompletedEvent(task_id="t1", status="COMPLETED", file_count=0)
        assert event.duration_seconds is None
