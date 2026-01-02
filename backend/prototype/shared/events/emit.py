import os
import requests
from .models import Event
from shared.logger import get_logger

logger = get_logger("EventEmitter")

FASTAPI_EVENT_ENDPOINT = os.getenv("FASTAPI_EVENT_ENDPOINT", "http://backend:8000/stream/event")


def emit_event(**kwargs):
    """
    Builds an Event with validation and sends it to the backend.
    """

    event = Event(**kwargs)

    try:
        requests.post(
            FASTAPI_EVENT_ENDPOINT,
            json=event.model_json_schema() and event.model_dump(),
            timeout=0.3,
        )
    except Exception as e:
        logger.exception(f"Failed to emit event: {e}")