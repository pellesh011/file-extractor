from app.core.exceptions import DomainError


class InvalidStatusTransitionError(DomainError):
    def __init__(self, entity: str, from_status: str, to_status: str) -> None:
        self.entity = entity
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition {entity} from {from_status} to {to_status}")


class FileAlreadyUploadedError(DomainError):
    def __init__(self, file_id: str) -> None:
        self.file_id = file_id
        super().__init__(f"File {file_id} is already uploaded")


class InvalidFileHashError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid file hash: {value!r}. Must be a 64-character SHA256 hex string")


class NegativeFileSizeError(DomainError):
    def __init__(self, value: int) -> None:
        self.value = value
        super().__init__(f"File size cannot be negative: {value}")


class InvalidFileIdError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid file ID: {value!r}. Must be a valid UUID")


class TaskAlreadyCompletedError(DomainError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Download task {task_id} is already completed")


class TaskNotRunningError(DomainError):
    def __init__(self, task_id: str, status: str) -> None:
        self.task_id = task_id
        self.status = status
        super().__init__(f"Download task {task_id} is in status {status}, expected RUNNING")
