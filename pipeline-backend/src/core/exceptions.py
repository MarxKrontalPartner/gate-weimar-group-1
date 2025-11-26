from typing import Any


class AppException(Exception):
    """
    Base exception class for application errors.
    
    All custom exceptions should inherit from this.
    This allows us to catch all app-specific errors in one place.
    """
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """
    Raised when a requested resource is not found.
    
    Example:
        raise NotFoundException(f"Pipeline with id {pipeline_id} not found")
    """
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=404, details=details)


class BadRequestException(AppException):
    """
    Raised when the request is invalid.
    
    Example:
        raise BadRequestException("Pipeline name cannot be empty")
    """
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=400, details=details)


class UnauthorizedException(AppException):
    """
    Raised when authentication is required but not provided or invalid.
    
    Example:
        raise UnauthorizedException("Invalid token")
    """
    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=401, details=details)


class ForbiddenException(AppException):
    """
    Raised when user is authenticated but doesn't have permission.
    
    Example:
        raise ForbiddenException("You don't have permission to delete this pipeline")
    """
    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=403, details=details)


class ConflictException(AppException):
    """
    Raised when there's a conflict (e.g., duplicate resource).
    
    Example:
        raise ConflictException(f"Pipeline with name '{name}' already exists")
    """
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=409, details=details)


class DatabaseException(AppException):
    """
    Raised when a database operation fails.
    
    Example:
        raise DatabaseException("Failed to connect to database")
    """
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=500, details=details)