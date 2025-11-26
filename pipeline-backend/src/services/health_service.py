from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.schemas.health import HealthResponse
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class HealthService:
    """
    Business logic for health checks.
    
    Separating logic into services means:
    - Routes stay thin (just handle HTTP)
    - Logic is testable without starting a web server
    - Can reuse logic in multiple routes
    """
    
    @staticmethod
    async def check_health(db: AsyncSession) -> HealthResponse:
        """
        Perform health check including database connectivity.
        
        Args:
            db: Database session
            
        Returns:
            HealthResponse with service status
            
        Raises:
            Exception: If database connection fails
        """
        try:
            # Test database connection with simple query
            result = await db.execute(text("SELECT 1"))
            result.fetchone()
            
            db_status = "connected"
            logger.info("Health check passed - database connected")
            
        except Exception as e:
            db_status = "disconnected"
            logger.error(f"Health check failed - database error: {str(e)}")
            raise
        
        return HealthResponse(
            status="healthy",
            version=settings.VERSION,
            database=db_status,
        )