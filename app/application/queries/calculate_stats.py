from dataclasses import dataclass


@dataclass
class CalculateStatsQuery:
    file_ids: list[str]


@dataclass
class CalculateStatsResult:
    overall: dict[str, int]
    per_file: dict[str, dict[str, int]]
