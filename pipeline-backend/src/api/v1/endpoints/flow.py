from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.flow import Flow, PipelineFlow
from src.models.database.pipeline import Pipeline

# Import Schemas
from src.schemas.flow import FlowCreate, FlowResponse, FlowUpdate

router = APIRouter()

# ------------------------------------------------------------------
# 1. CREATE Flow & Link to Pipeline
# POST /api/v1/pipeline/{pipeline_id}/flow
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/flow", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
async def create_flow_for_pipeline(
    pipeline_id: int, 
    flow_in: FlowCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Flow (connection between nodes) and link it to the Pipeline.
    """
    # 1. Validate Pipeline exists
    pipeline_query = select(Pipeline).where(Pipeline.pipeline_id == pipeline_id)
    pipeline_result = await db.execute(pipeline_query)
    pipeline = pipeline_result.scalars().first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Pipeline with ID {pipeline_id} not found"
        )

    # 2. Create the Flow object
    new_flow = Flow(**flow_in.model_dump())
    db.add(new_flow)
    
    # 3. Flush to generate the ID
    await db.flush()

    # 4. Create the link in the Junction Table
    new_link = PipelineFlow(
        pipeline_id=pipeline_id,
        flow_id=new_flow.flow_id
    )
    db.add(new_link)

    # 5. Commit
    await db.commit()
    await db.refresh(new_flow)
    
    return new_flow


# ------------------------------------------------------------------
# 2. LIST Flows for a Pipeline
# GET /api/v1/pipeline/{pipeline_id}/flow
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/flow", response_model=List[FlowResponse])
async def read_flows(
    pipeline_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all Flows (connections) associated with a specific Pipeline.
    """
    query = (
        select(Flow)
        .join(PipelineFlow, Flow.flow_id == PipelineFlow.flow_id)
        .where(PipelineFlow.pipeline_id == pipeline_id)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------
# 3. GET ONE Flow (Verified by Pipeline)
# GET /api/v1/pipeline/{pipeline_id}/flow/{flow_id}
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/flow/{flow_id}", response_model=FlowResponse)
async def read_flow(
    pipeline_id: int, 
    flow_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific flow, ensuring it actually belongs to the pipeline.
    """
    query = (
        select(Flow)
        .join(PipelineFlow, Flow.flow_id == PipelineFlow.flow_id)
        .where(
            PipelineFlow.pipeline_id == pipeline_id,
            Flow.flow_id == flow_id
        )
    )
    
    result = await db.execute(query)
    flow_obj = result.scalars().first()

    if not flow_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Flow not found or not associated with this pipeline"
        )

    return flow_obj


# ------------------------------------------------------------------
# 4. UPDATE Flow
# PUT /api/v1/pipeline/{pipeline_id}/flow/{flow_id}
# ------------------------------------------------------------------
@router.put("/{pipeline_id}/flow/{flow_id}", response_model=FlowResponse)
async def update_flow(
    pipeline_id: int, 
    flow_id: int, 
    flow_update: FlowUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Find the flow
    query = (
        select(Flow)
        .join(PipelineFlow, Flow.flow_id == PipelineFlow.flow_id)
        .where(
            PipelineFlow.pipeline_id == pipeline_id,
            Flow.flow_id == flow_id
        )
    )
    result = await db.execute(query)
    flow_obj = result.scalars().first()

    if not flow_obj:
        raise HTTPException(status_code=404, detail="Flow not found")

    # 2. Update fields
    update_data = flow_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(flow_obj, key, value)

    # 3. Save
    db.add(flow_obj)
    await db.commit()
    await db.refresh(flow_obj)

    return flow_obj


# ------------------------------------------------------------------
# 5. DELETE Flow
# DELETE /api/v1/pipeline/{pipeline_id}/flow/{flow_id}
# ------------------------------------------------------------------
@router.delete("/{pipeline_id}/flow/{flow_id}", status_code=status.HTTP_200_OK)
async def delete_flow(
    pipeline_id: int, 
    flow_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes the Flow connection.
    """
    # 1. Fetch
    query = (
        select(Flow)
        .join(PipelineFlow, Flow.flow_id == PipelineFlow.flow_id)
        .where(
            PipelineFlow.pipeline_id == pipeline_id,
            Flow.flow_id == flow_id
        )
    )
    result = await db.execute(query)
    flow_obj = result.scalars().first()

    if not flow_obj:
        raise HTTPException(status_code=404, detail="Flow not found")

    # 2. Delete
    await db.delete(flow_obj)
    await db.commit()

    return {"message": "Flow deleted successfully", "flow_id": flow_id}