from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class TransformationBase(BaseModel):
    name: str
    description: Optional[str] = None
    schema_in: Optional[Dict[str, Any]] = None  # JSON field
    schema_out: Optional[Dict[str, Any]] = None # JSON field
    python_script: str

class TransformationCreate(TransformationBase):
    pass

class TransformationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schema_in: Optional[Dict[str, Any]] = None
    schema_out: Optional[Dict[str, Any]] = None
    python_script: Optional[str] = None

class TransformationResponse(TransformationBase):
    transformation_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)