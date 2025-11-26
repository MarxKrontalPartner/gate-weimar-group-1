from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the tag (e.g. 'Production', 'Draft')")

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    tag_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)