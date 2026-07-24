from __future__ import annotations

from enum import Enum, auto


class FileStatus(Enum):
    CREATED = auto()
    UPLOADING = auto()
    UPLOADED = auto()
    FAILED = auto()


class TaskStatus(Enum):
    CREATED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
