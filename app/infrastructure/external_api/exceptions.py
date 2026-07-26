from __future__ import annotations


class ExternalAPIRetryableError(Exception):
    pass


class ExternalAPIRateLimitedError(ExternalAPIRetryableError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class ExternalAPIBlockedError(ExternalAPIRetryableError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Blocked. Retry after {retry_after}s")


class ExternalAPIForbiddenError(Exception):
    pass


class ExternalAPINotFoundError(Exception):
    pass


class ExternalAPIServerError(Exception):
    pass


class ExternalAPIParseError(Exception):
    pass
