from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- Shared Properties ---
class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None

# --- Input Schema (POST /api/pipeline) ---
class PipelineCreate(PipelineBase):
    pass

# --- Update Schema (PUT /api/pipeline/{id}) ---
class PipelineUpdate(BaseModel):
    # Everything is optional because the user might update only one field
    name: Optional[str] = None
    description: Optional[str] = None

# --- Output Schema (GET/POST Response) ---
class PipelineResponse(PipelineBase):
    pipeline_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # This allows Pydantic to read data from SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)