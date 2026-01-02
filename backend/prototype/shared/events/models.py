from typing import Any, Optional
from pydantic import BaseModel

class Event(BaseModel):
    pipeline_id: str
    segment_index: Optional[int] = None
    category: str   
    type: str       
    topic: Optional[str] = None
    data: Any = None