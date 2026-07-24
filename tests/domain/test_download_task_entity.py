import pytest

from app.domain.entities.download_task import DownloadTask
from app.domain.exceptions import InvalidStatusTransitionError, TaskNotRunningError
from app.domain.value_objects import TaskStatus


@pytest.fixture
def task() -> DownloadTask:
    return DownloadTask(task_id="task-1", candidate_id="candidate-1")


class TestTaskCreation:
    def test_default_status(self, task: DownloadTask) -> None:
        assert task.status == TaskStatus.CREATED
        assert task.received_files == 0
        assert task.processed_files == 0
        assert task.error is None
        assert task.started_at is None
        assert task.finished_at is None


class TestTaskLifecycle:
    def test_full_lifecycle(self, task: DownloadTask) -> None:
        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

        task.increase_received(5)
        assert task.received_files == 5

        task.increase_processed(3)
        assert task.processed_files == 3

        task.complete()
        assert task.status == TaskStatus.COMPLETED
        assert task.finished_at is not None

    def test_increase_received_and_processed(self, task: DownloadTask) -> None:
        task.start()
        task.increase_received(10)
        task.increase_received(5)
        assert task.received_files == 15
        task.increase_processed(7)
        assert task.processed_files == 7


class TestTaskFail:
    def test_fail_from_created(self, task: DownloadTask) -> None:
        task.fail("something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.error == "something went wrong"
        assert task.finished_at is not None

    def test_fail_from_running(self, task: DownloadTask) -> None:
        task.start()
        task.fail("error")
        assert task.status == TaskStatus.FAILED

    def test_cannot_fail_from_completed(self, task: DownloadTask) -> None:
        task.start()
        task.complete()
        with pytest.raises(InvalidStatusTransitionError):
            task.fail("too late")


class TestTaskInvalidTransitions:
    def test_cannot_start_twice(self, task: DownloadTask) -> None:
        task.start()
        with pytest.raises(InvalidStatusTransitionError):
            task.start()

    def test_cannot_complete_from_created(self, task: DownloadTask) -> None:
        with pytest.raises(InvalidStatusTransitionError):
            task.complete()

    def test_increase_received_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.increase_received(1)

    def test_increase_processed_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.increase_processed(1)
