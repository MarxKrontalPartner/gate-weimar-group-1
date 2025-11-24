from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Pydantic automatically:
    - Validates the data structure
    - Generates OpenAPI/Swagger documentation
    - Serializes to JSON
    """
    status: str = Field(..., description="Service status", examples=["healthy"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    database: str = Field(..., description="Database connection status", examples=["connected"])
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "database": "connected"
            }
        }