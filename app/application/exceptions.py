from __future__ import annotations


class ExternalAPIBlockedError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Blocked. Retry after {retry_after}s")
