from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Import the Enum from the database model to ensure consistency
from src.models.database.flow import NodeType

class FlowBase(BaseModel):
    start_node_type: NodeType
    end_node_type: NodeType
    start_node: int  # ID of the starting node (input_id or transformation_id)
    end_node: int    # ID of the ending node (transformation_id or output_id)

class FlowCreate(FlowBase):
    pass

class FlowUpdate(BaseModel):
    start_node_type: Optional[NodeType] = None
    end_node_type: Optional[NodeType] = None
    start_node: Optional[int] = None
    end_node: Optional[int] = None

class FlowResponse(FlowBase):
    flow_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)