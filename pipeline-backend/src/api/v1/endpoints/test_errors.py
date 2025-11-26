from fastapi import APIRouter

from src.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)

router = APIRouter()


@router.get("/test/not-found")
async def test_not_found() -> None:
    """Test 404 error handling."""
    raise NotFoundException("Test resource not found")


@router.get("/test/bad-request")
async def test_bad_request() -> None:
    """Test 400 error handling."""
    raise BadRequestException("Test invalid request")


@router.get("/test/conflict")
async def test_conflict() -> None:
    """Test 409 error handling."""
    raise ConflictException("Test duplicate resource")


@router.get("/test/server-error")
async def test_server_error() -> None:
    """Test 500 error handling."""
    # Deliberately cause an error
    result = 1 / 0  # ZeroDivisionError
    return {"result": result}