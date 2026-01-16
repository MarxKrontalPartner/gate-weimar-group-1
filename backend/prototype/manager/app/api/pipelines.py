# app/api/pipelines.py
from typing import List
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException

from app.pipelines.models import PipelineInput
from app.pipelines.lifecycle import manage_pipeline_lifecycle
from app.pipelines.registry import (
    init_pipeline,
    segment_completed,
    fail_pipeline,
    get_pipeline,
    abort_pipeline,
)
from app.ws.manager import ConnectionManager
from shared.events import Event
from shared.logger import get_logger
import docker

router = APIRouter()
manager = ConnectionManager()
logger = get_logger("API")

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

    state = get_pipeline(pipeline_id)
    current_status = state["status"] if state else None

    if event_category == "lifecycle":
        if current_status == "aborted":
            return {"ignored": True}
        
        completed_now = False
        if event_type == "segment_completed":
            completed_now = segment_completed(pipeline_id)

        elif event_type == "failed":
            fail_pipeline(pipeline_id, data)

        await manager.broadcast({
            "category": event_category,
            "type": event_type,
            "pipeline_id": pipeline_id,
            "data": data,
        })
        # Emit completion when pipeline transitions to COMPLETED
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

@router.post("/abort/{pipeline_id}")
async def abort_pipeline_api(pipeline_id: str):
    state = get_pipeline(pipeline_id)

    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if state["status"] in ("completed", "failed", "aborted"):
        return {"status": "ignored", "reason": "pipeline already finished"}

    # register abort
    changed = abort_pipeline(pipeline_id)
    if not changed:
        return {"status": "ignored", "reason": "cannot abort"}

    client = docker.from_env()

    # kill containers (if any) for this pipeline
    containers = client.containers.list(
        all=True,
        filters={"label": f"pipeline_id={pipeline_id}"}
    )

    for c in containers:
        try:
            logger.info(f"[{pipeline_id}] Aborting container {c.name}")
            c.stop()
            c.remove()
        except Exception as e:
            logger.warning(f"Error aborting container {c.name}: {e}")

    await manager.broadcast({
        "category": "lifecycle",
        "type": "aborted",
        "pipeline_id": pipeline_id,
        "data": None,
    })

    return {"status": "aborted"}