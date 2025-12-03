import logging
import sys
from typing import Any

from src.core.config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Create a configured logger instance.
    
    Args:
        name: Logger name (usually __name__ of the module using it)
    
    Returns:
        Configured logger that writes to stdout with timestamps
    
    Example:
        logger = setup_logger(__name__)
        logger.info("Something happened")
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    
    # Don't add handlers if they already exist (prevents duplicate logs)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.LOG_LEVEL)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger