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


class CategoryError(ServiceError):
    """Base class for category related errors."""


class CategoryNotFoundError(CategoryError):
    """Raised when the requested category does not exist."""


class CategoryAlreadyExistsError(CategoryError):
    """Raised when creating or renaming a category conflicts with an existing one."""
