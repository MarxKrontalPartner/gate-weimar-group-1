from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.output import Output, PipelineOutput
from src.models.database.pipeline import Pipeline

# Import Schemas
from src.schemas.output import OutputCreate, OutputResponse, OutputUpdate

router = APIRouter()

# ------------------------------------------------------------------
# 1. CREATE Output & Link to Pipeline
# POST /api/v1/pipeline/{pipeline_id}/output
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/output", response_model=OutputResponse, status_code=status.HTTP_201_CREATED)
async def create_output_for_pipeline(
    pipeline_id: int, 
    output_new: OutputCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Output and link it to the specified Pipeline.
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

    # 2. Create the Output object
    new_output = Output(**output_new.model_dump())
    db.add(new_output)
    
    # 3. Flush to generate the new_output.output_id without closing the transaction
    await db.flush()

    # 4. Create the link in the Junction Table
    new_link = PipelineOutput(
        pipeline_id=pipeline_id,
        output_id=new_output.output_id
    )
    db.add(new_link)

    # 5. Commit everything properly
    await db.commit()
    await db.refresh(new_output)
    
    return new_output


# ------------------------------------------------------------------
# 2. LIST Outputs for a Pipeline
# GET /api/v1/pipeline/{pipeline_id}/output
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/output", response_model=List[OutputResponse])
async def read_outputs(
    pipeline_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all Outputs associated with a specific Pipeline.
    """
    query = (
        select(Output)
        .join(PipelineOutput, Output.output_id == PipelineOutput.output_id)
        .where(PipelineOutput.pipeline_id == pipeline_id)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------
# 3. GET ONE Output (Verified by Pipeline)
# GET /api/v1/pipeline/{pipeline_id}/output/{output_id}
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/output/{output_id}", response_model=OutputResponse)
async def read_output(
    pipeline_id: int, 
    output_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific output, ensuring it actually belongs to the pipeline.
    """
    query = (
        select(Output)
        .join(PipelineOutput, Output.output_id == PipelineOutput.output_id)
        .where(
            PipelineOutput.pipeline_id == pipeline_id,
            Output.output_id == output_id
        )
    )
    
    result = await db.execute(query)
    output_obj = result.scalars().first()

    if not output_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Output not found or not associated with this pipeline"
        )

    return output_obj


# ------------------------------------------------------------------
# 4. UPDATE Output
# PUT /api/v1/pipeline/{pipeline_id}/output/{output_id}
# ------------------------------------------------------------------
@router.put("/{pipeline_id}/output/{output_id}", response_model=OutputResponse)
async def update_output(
    pipeline_id: int, 
    output_id: int, 
    output_update: OutputUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Find the output (ensuring it belongs to the pipeline)
    query = (
        select(Output)
        .join(PipelineOutput, Output.output_id == PipelineOutput.output_id)
        .where(
            PipelineOutput.pipeline_id == pipeline_id,
            Output.output_id == output_id
        )
    )
    result = await db.execute(query)
    output_obj = result.scalars().first()

    if not output_obj:
        raise HTTPException(status_code=404, detail="Output not found")

    # 2. Update fields
    update_data = output_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(output_obj, key, value)

    # 3. Save
    db.add(output_obj)
    await db.commit()
    await db.refresh(output_obj)

    return output_obj


# ------------------------------------------------------------------
# 5. DELETE Output
# DELETE /api/v1/pipeline/{pipeline_id}/output/{output_id}
# ------------------------------------------------------------------
@router.delete("/{pipeline_id}/output/{output_id}", status_code=status.HTTP_200_OK)
async def delete_output(
    pipeline_id: int, 
    output_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes the Output object entirely. 
    Cascade rules in DB will automatically remove the link in PipelineOutput.
    """
    # 1. Fetch the output
    query = (
        select(Output)
        .join(PipelineOutput, Output.output_id == PipelineOutput.output_id)
        .where(
            PipelineOutput.pipeline_id == pipeline_id,
            Output.output_id == output_id
        )
    )
    result = await db.execute(query)
    output_obj = result.scalars().first()

    if not output_obj:
        raise HTTPException(status_code=404, detail="Output not found")

    # 2. Delete
    await db.delete(output_obj)
    await db.commit()

    return {"message": "Output deleted successfully", "output_id": output_id}