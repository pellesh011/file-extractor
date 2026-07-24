from dataclasses import dataclass


@dataclass
class StartDownloadCommand:
    candidate_id: str | None = None
