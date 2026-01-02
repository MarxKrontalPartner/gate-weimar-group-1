import logging

# Define log format and date format
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] : %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level=logging.INFO):
    """
    Set up logging configuration.

    Parameters
    ----------
    level : int
        Logging level (default is logging.INFO).
    """
    logging.basicConfig(format=LOG_FORMAT, datefmt=DATE_FORMAT, level=level, force=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Parameters
    ----------
    name : str
        Name of the logger.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    setup_logging()
    return logging.getLogger(name)
