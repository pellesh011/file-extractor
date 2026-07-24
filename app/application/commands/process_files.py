from dataclasses import dataclass


@dataclass
class ProcessFilesCommand:
    task_id: str
    candidate_id: str | None = None
