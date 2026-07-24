from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class FileUploadedEvent:
    file_id: str
    storage_key: str
    filename: str
    size: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
