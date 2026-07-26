import pytest

from app.domain.entities.download_task import DownloadTask
from app.domain.exceptions import InvalidStatusTransitionError, TaskNotRunningError
from app.domain.value_objects import TaskStatus


@pytest.fixture
def task() -> DownloadTask:
    return DownloadTask(task_id="task-1", candidate_id="candidate-1")


class TestTaskCreation:
    def test_default_status(self, task: DownloadTask) -> None:
        assert task.status == TaskStatus.PENDING
        assert task.received_files == 0
        assert task.processed_files == 0
        assert task.error is None
        assert task.started_at is None
        assert task.finished_at is None
        assert task.worker_id is None
        assert task.last_heartbeat is None
        assert task.attempts == 0
        assert task.blocked_until is None
        assert task.block_reason is None


class TestTaskLifecycle:
    def test_full_lifecycle(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        assert task.worker_id == "worker-1"
        assert task.last_heartbeat is not None
        assert task.attempts == 1

        task.increase_received(5)
        assert task.received_files == 5

        task.increase_processed(3)
        assert task.processed_files == 3

        task.complete()
        assert task.status == TaskStatus.SUCCESS
        assert task.finished_at is not None

    def test_increase_received_and_processed(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        task.increase_received(10)
        task.increase_received(5)
        assert task.received_files == 15
        task.increase_processed(7)
        assert task.processed_files == 7


class TestTaskFail:
    def test_fail_from_pending(self, task: DownloadTask) -> None:
        task.fail("something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.error == "something went wrong"
        assert task.finished_at is not None

    def test_fail_from_running(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        task.fail("error")
        assert task.status == TaskStatus.FAILED

    def test_cannot_fail_from_success(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        task.complete()
        with pytest.raises(InvalidStatusTransitionError):
            task.fail("too late")


class TestTaskBlock:
    def test_block_from_running(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        task.block(300, reason="rate limited")
        assert task.status == TaskStatus.BLOCKED
        assert task.blocked_until is not None
        assert task.block_reason == "rate limited"
        assert task.error is not None

    def test_block_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.block(300)

    def test_is_blocked_when_expired(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        task.block(-1)
        assert not task.is_blocked()


class TestTaskHeartbeat:
    def test_heartbeat_updates_timestamp(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        old = task.last_heartbeat
        assert old is not None
        task.heartbeat()
        assert task.last_heartbeat is not None
        assert task.last_heartbeat >= old

    def test_heartbeat_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.heartbeat()


class TestTaskClaim:
    def test_claim_increments_attempts(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        assert task.attempts == 1
        assert task.worker_id == "worker-1"

    def test_claim_twice_fails(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        with pytest.raises(InvalidStatusTransitionError):
            task.claim("worker-2")


class TestTaskInvalidTransitions:
    def test_cannot_claim_twice(self, task: DownloadTask) -> None:
        task.claim("worker-1")
        with pytest.raises(InvalidStatusTransitionError):
            task.claim("worker-1")

    def test_cannot_complete_from_pending(self, task: DownloadTask) -> None:
        with pytest.raises(InvalidStatusTransitionError):
            task.complete()

    def test_increase_received_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.increase_received(1)

    def test_increase_processed_not_running(self, task: DownloadTask) -> None:
        with pytest.raises(TaskNotRunningError):
            task.increase_processed(1)
