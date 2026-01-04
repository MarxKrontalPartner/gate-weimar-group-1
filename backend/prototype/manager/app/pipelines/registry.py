# app/pipelines/registry.py
from typing import Dict
from threading import Lock
from datetime import datetime
from zoneinfo import ZoneInfo
from app.pipelines.models import PipelineStatus


class PipelineState:
    def __init__(self, pipeline_id: str, total_segments: int):
        self.pipeline_id = pipeline_id
        self.total_segments = total_segments
        self.completed_segments = 0
        self.status = PipelineStatus.STARTING
        self.message = "Pipeline initialized"
        self.created_at = datetime.now(ZoneInfo("Europe/Berlin"))
        self.lock = Lock()
        self._completion_emitted = False

    def to_dict(self):
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "completed_segments": self.completed_segments,
            "total_segments": self.total_segments,
            "message": self.message,
        }


PIPELINES: Dict[str, PipelineState] = {}


def init_pipeline(pipeline_id: str, total_segments: int):
    if pipeline_id in PIPELINES:
        return PIPELINES[pipeline_id]

    PIPELINES[pipeline_id] = PipelineState(
        pipeline_id=pipeline_id,
        total_segments=total_segments,
    )
    return PIPELINES[pipeline_id]


def segment_completed(pipeline_id: str) -> bool:
    """
    Returns True ONLY if pipeline transitions to COMPLETED
    """
    pipeline = PIPELINES.get(pipeline_id)
    if not pipeline:
        return False

    with pipeline.lock:
        if pipeline.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
            return False

        pipeline.status = PipelineStatus.RUNNING
        pipeline.completed_segments += 1

        if pipeline.completed_segments >= pipeline.total_segments:
            pipeline.status = PipelineStatus.COMPLETED
            pipeline.message = "Pipeline completed"
            if not pipeline._completion_emitted:
                pipeline._completion_emitted = True
                return True

    return False


def fail_pipeline(pipeline_id: str, message: str):
    pipeline = PIPELINES.get(pipeline_id)
    if not pipeline:
        return

    with pipeline.lock:
        if pipeline.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
            return

        pipeline.status = PipelineStatus.FAILED
        pipeline.message = message


def get_pipeline(pipeline_id: str):
    pipeline = PIPELINES.get(pipeline_id)
    return pipeline.to_dict() if pipeline else None
