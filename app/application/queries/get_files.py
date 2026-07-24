from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GetFilesQuery:
    page: int = 1
    per_page: int = 20
    status: str | None = None


@dataclass
class FileItem:
    id: str
    filename: str
    size: int
    status: str
    hash: str | None
    created_at: datetime
    uploaded_at: datetime | None


@dataclass
class GetFilesResult:
    items: list[FileItem]
    total: int
    page: int
    per_page: int
