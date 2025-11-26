from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Import Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.pipeline import Pipeline

# Import Services
from src.services.validation_service import ValidationService

# Import Schemas
from src.schemas.execution import ExecutionResponse, StatusResponse

from src.services.execution_manager_quix import QuixPipelineManager

router = APIRouter()

# ------------------------------------------------------------------
# 1. VALIDATE (REAL IMPLEMENTATION)
# POST /api/v1/pipeline/{pipeline_id}/validate
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/validate", response_model=ExecutionResponse)
async def validate_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a comprehensive validation check on the pipeline.
    Checks:
    1. Connectivity: Can we reach the Kafka Brokers?
    2. Structure: Are there cycles or invalid connections?
    3. Schema: Do the data types align?
    """
    # 1. Run the validation service
    # We pass the DB session so the service can fetch everything it needs
    result = await ValidationService.validate_pipeline(pipeline_id, db)

    # 2. Process results
    if result["valid"]:
        msg = "Validation Successful. Pipeline is ready to start."
        status_code = "valid"
        if result["warnings"]:
            msg += f" (Warnings: {'; '.join(result['warnings'])})"
    else:
        # If invalid, we list the errors in the message
        msg = f"Validation Failed: {'; '.join(result['errors'])}"
        status_code = "invalid"

    return {
        "message": msg,
        "pipeline_id": pipeline_id,
        "status": status_code
    }

# ------------------------------------------------------------------
# 2. START Execution (REAL)
# POST /api/v1/pipeline/{pipeline_id}/start
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/start", response_model=ExecutionResponse)
async def start_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Start the pipeline execution.
    Spins up a background worker that consumes Kafka -> Transforms -> Produces Kafka.
    """
    try:
        # 1. Validate first (Optional, but good practice)
        val_result = await ValidationService.validate_pipeline(pipeline_id, db)
        if not val_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot start invalid pipeline: {val_result['errors']}"
            )

        # 2. Start via Manager
        result = await QuixPipelineManager.start_pipeline(pipeline_id, db)
        
        return {
            "message": "Pipeline execution started successfully.",
            "pipeline_id": pipeline_id,
            "status": result["status"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


# ------------------------------------------------------------------
# 3. STOP Execution (REAL)
# POST /api/v1/pipeline/{pipeline_id}/stop
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/stop", response_model=ExecutionResponse)
async def stop_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Stop the pipeline execution.
    Gracefully disconnects consumers and producers.
    """
    try:
        result = await QuixPipelineManager.stop_pipeline(pipeline_id)
        return {
            "message": "Pipeline execution stopped.",
            "pipeline_id": pipeline_id,
            "status": result["status"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# 4. GET STATUS (REAL)
# GET /api/v1/pipeline/{pipeline_id}/status
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/status", response_model=StatusResponse)
async def get_pipeline_status(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time metrics from the running background task.
    """
    # We don't need the DB session here because status is in memory
    status_data = QuixPipelineManager.get_status(pipeline_id)
    
    return {
        "pipeline_id": pipeline_id,
        "status": status_data["status"],
        "uptime": status_data["uptime"],
        "details": status_data["details"]
    }