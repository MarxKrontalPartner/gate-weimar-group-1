from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.exceptions import AppException
from src.schemas.error import ErrorDetail, ErrorResponse
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.
    
    These are exceptions we deliberately raise in our business logic.
    """
    logger.warning(
        f"Application exception: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "details": exc.details,
        },
    )
    
    error_response = ErrorResponse(
        error=exc.__class__.__name__,
        message=exc.message,
        details=exc.details if exc.details else None,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    These occur when request data doesn't match the expected schema.
    """
    # Convert Pydantic errors to our error format
    error_details = []
    for error in exc.errors():
        error_details.append(
            ErrorDetail(
                field=".".join(str(loc) for loc in error["loc"]),
                message=error["msg"],
                type=error["type"],
            ).model_dump()
        )
    
    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "errors": error_details,
        },
    )
    
    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        details=error_details,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """
    Handle database integrity errors (unique constraints, foreign keys, etc.).
    
    These occur when database constraints are violated.
    """
    logger.error(
        f"Database integrity error: {str(exc.orig)}",
        extra={"path": request.url.path},
        exc_info=True,
    )
    
    # Try to make the error message user-friendly
    error_message = "Database constraint violation"
    if "unique" in str(exc.orig).lower():
        error_message = "A record with this value already exists"
    elif "foreign key" in str(exc.orig).lower():
        error_message = "Referenced resource does not exist"
    
    error_response = ErrorResponse(
        error="IntegrityError",
        message=error_message,
        details={"database_error": str(exc.orig)},
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(),
    )


async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """
    Handle general database errors.
    
    These are unexpected database issues (connection failures, etc.).
    """
    logger.error(
        f"Database error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        error="DatabaseError",
        message="A database error occurred",
        details=None,  # Don't expose internal database errors to users
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unexpected exceptions.
    
    This is the catch-all for errors we didn't anticipate.
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={"path": request.url.path},
        exc_info=True,
    )
    
    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        details=None,  # Don't expose internal errors to users
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )