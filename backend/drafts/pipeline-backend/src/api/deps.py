from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency for route handlers.
    """
    async for session in get_db():
        yield session