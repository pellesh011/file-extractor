class AppError(Exception):
    """Base exception for the application."""


class DomainError(AppError):
    """Base exception for domain layer errors."""


class ApplicationError(AppError):
    """Base exception for application layer errors."""


class InfrastructureError(AppError):
    """Base exception for infrastructure layer errors."""
