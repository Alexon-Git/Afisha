"""Custom exceptions used by the service layer."""


class ServiceError(RuntimeError):
    """Base class for service layer errors."""


class UserAlreadyExistsError(ServiceError):
    """Raised when attempting to create a user that already exists."""


class EventNotFoundError(ServiceError):
    """Raised when an event with the requested identifier does not exist."""


class InvalidImageError(ServiceError):
    """Raised when an uploaded image does not meet validation rules."""


class InvalidDateFilterError(ServiceError):
    """Raised when provided date filters cannot be parsed."""
