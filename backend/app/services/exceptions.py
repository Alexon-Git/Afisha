"""Custom exceptions used by the service layer."""


class ServiceError(RuntimeError):
    """Base class for service layer errors."""


class UserAlreadyExistsError(ServiceError):
    """Raised when attempting to create a user that already exists."""


class EventNotFoundError(ServiceError):
    """Raised when an event with the requested identifier does not exist."""


class OrganizerNotFoundError(ServiceError):
    """Raised when the assigned organizer does not exist."""


class PublicationValidationError(ServiceError):
    def __init__(self, fields):
        self.fields = fields
        super().__init__("Event does not meet publication requirements")


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


class ArticleNotFoundError(ServiceError):
    """Raised when an article does not exist or is not public."""


class ArticleConflictError(ServiceError):
    """Raised on duplicate or immutable slug."""


class ArticleValidationError(ServiceError):
    def __init__(self, fields):
        self.fields = fields
        super().__init__("Article does not meet publication requirements")
