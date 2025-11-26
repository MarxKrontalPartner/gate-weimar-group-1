from functools import lru_cache
from typing import List

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses pydantic-settings to:
    - Load from .env file automatically
    - Validate types
    - Provide defaults
    """
    # Database Credentials for container
    POSTGRES_USER : str
    POSTGRES_PASSWORD : str
    POSTGRES_DB : str 
    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Pipeline Backend"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Create settings instance (cached).
    
    @lru_cache means this function only runs once,
    then returns the same Settings object every time.
    This is efficient and ensures consistent config across your app.
    """
    return Settings()


# Convenience: import settings directly
settings = get_settings()