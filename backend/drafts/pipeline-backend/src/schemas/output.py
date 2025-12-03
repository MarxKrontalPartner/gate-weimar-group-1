from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class OutputBase(BaseModel):
    name: str
    description: Optional[str] = None
    topic: str
    schemas: Optional[Dict[str, Any]] = None  
    broker_address: str

class OutputCreate(OutputBase):
    pass

class OutputUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    topic: Optional[str] = None
    schemas: Optional[Dict[str, Any]] = None
    broker_address: Optional[str] = None

class OutputResponse(OutputBase):
    output_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)