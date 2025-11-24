from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db_session
from src.schemas.health import HealthResponse
from src.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the API and database are operational",
    tags=["Health"],
)
async def health_check(
    db: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status including database connectivity.
    Useful for load balancers and monitoring systems.
    """
    return await HealthService.check_health(db)