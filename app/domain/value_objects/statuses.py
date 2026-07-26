from __future__ import annotations

from enum import Enum, auto


class FileStatus(Enum):
    CREATED = auto()
    UPLOADING = auto()
    UPLOADED = auto()
    FAILED = auto()


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    BLOCKED = auto()
