from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class InputBase(BaseModel):
    name: str
    description: str
    topic: str
    schemas: Optional[Dict[str, Any]] = None 
    broker_address: str


class InputCreate(InputBase):
    pass

class InputUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    topic: Optional[str] = None
    schemas: Optional[Dict[str, Any]] = None 
    broker_address: Optional[str] = None

class InputResponse(InputBase):
    input_id : int
    created_at : datetime

    model_config = ConfigDict(from_attributes = True)





