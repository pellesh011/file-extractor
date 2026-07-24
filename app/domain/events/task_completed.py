from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TaskCompletedEvent:
    task_id: str
    status: str
    file_count: int
    duration_seconds: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
