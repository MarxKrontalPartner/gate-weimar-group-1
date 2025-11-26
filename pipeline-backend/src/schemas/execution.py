from pydantic import BaseModel
from typing import Optional, Any

class ExecutionResponse(BaseModel):
    """Simple response for execution actions."""
    message: str
    pipeline_id: int
    status: Optional[str] = None

class StatusResponse(BaseModel):
    """Response for status polling."""
    pipeline_id: int
    status: str
    uptime: str
    details: Optional[Any] = None