from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GetStatisticsQuery:
    pass


@dataclass
class StatisticsResult:
    total_files: int = 0
    total_size: int = 0
    uploaded_files: int = 0
    failed_files: int = 0
    average_file_size: float = 0.0
