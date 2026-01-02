# app/api/pipelines.py
from typing import List
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect

from app.pipelines.models import PipelineInput
from app.pipelines.lifecycle import manage_pipeline_lifecycle
from app.pipelines.registry import (
    init_pipeline,
    segment_completed,
    fail_pipeline,
)
from app.ws.manager import ConnectionManager
from shared.events import Event

router = APIRouter()
manager = ConnectionManager()

@router.post("/start")
def start_pipeline(
    pipelines: List[PipelineInput],
    background_tasks: BackgroundTasks,
):
    pipeline_id = pipelines[0].pipeline_id

    init_pipeline(
        pipeline_id=pipeline_id,
        total_segments=len(pipelines),
    )

    for segment_idx, pipeline in enumerate(pipelines):
        background_tasks.add_task(manage_pipeline_lifecycle, pipeline, segment_idx)

    return {
        "status": "accepted",
        "pipeline_id": pipeline_id,
        "segments": len(pipelines),
    }

# -----------------------------
# WebSocket stream (UI listens)
# -----------------------------
@router.websocket("/ws/stream")
async def pipeline_ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -----------------------------
# Worker event ingestion
# -----------------------------
@router.post("/stream/event")
async def ingest_event(event: Event):
    pipeline_id = event.pipeline_id
    if not pipeline_id:
        return {"ignored": True}

    event_category = event.category
    event_type = event.type
    data = event.data

    if event_category == "lifecycle":
        completed_now = False
        if event_type == "segment_completed":
            completed_now = segment_completed(pipeline_id)

        elif event_type == "failed":
            fail_pipeline(pipeline_id, data)

        # Always broadcast authoritative state
        await manager.broadcast({
            "category": event_category,
            "type": event_type,
            "pipeline_id": pipeline_id,
            "data": data,
        })

        # Emit completion event ONCE
        if completed_now:
            await manager.broadcast({
                "category": event_category,
                "type": "completed",
                "pipeline_id": pipeline_id,
                "data": None,
            })
    
    elif event_category == "stream":
        await manager.broadcast(event.model_dump())
    
    else:
        pass  # Unknown category — ignore

    return {"ok": True}