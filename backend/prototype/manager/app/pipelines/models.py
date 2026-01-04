# app/pipelines/models.py
from pydantic import BaseModel
from enum import Enum

class PipelineInput(BaseModel):
    pipeline_id: str
    input_topic: str
    output_topic: str
    transformations: list[str]
    allow_producer: bool = False
    n_channels: int = 10
    frequency: float = 1.0
    runtime: int

class PipelineStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"