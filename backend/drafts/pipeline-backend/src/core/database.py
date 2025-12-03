from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.core.config import settings
from src.models.database.base import Base


# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session to route handlers.
    
    How this works:
    1. Creates a new database session
    2. Yields it to your route handler (the route uses it)
    3. After the route finishes, closes the session automatically
    
    The 'async with' ensures the session always closes,
    even if an error occurs.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close database connections gracefully.
    
    Call this when shutting down your application
    to cleanly close all database connections.
    """
    await engine.dispose()