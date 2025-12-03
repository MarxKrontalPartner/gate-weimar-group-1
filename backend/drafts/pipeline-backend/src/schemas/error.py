from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Detailed error information.
    
    Used for validation errors or additional context.
    """
    field: str | None = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: str | None = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    All errors return this structure for consistency.
    """
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | dict[str, Any] | None = Field(
        None,
        description="Additional error details",
    )
    path: str | None = Field(None, description="Request path that caused the error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "NotFoundError",
                "message": "Pipeline with id 123 not found",
                "details": None,
                "path": "/api/v1/pipelines/123",
            }
        }