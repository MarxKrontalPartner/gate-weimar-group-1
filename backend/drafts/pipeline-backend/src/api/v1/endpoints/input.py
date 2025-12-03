from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Import your Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.input import Input, PipelineInput
from src.models.database.pipeline import Pipeline

# Import Schemas
from src.schemas.input import InputCreate, InputResponse, InputUpdate

router = APIRouter()

# ------------------------------------------------------------------
# 1. CREATE Input & Link to Pipeline
# POST /api/v1/{pipeline_id}/input
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/input", response_model=InputResponse, status_code=status.HTTP_201_CREATED)
async def create_input_for_pipeline(
    pipeline_id: int, 
    input_new: InputCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Input and link it to the specified Pipeline.
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

    # 2. Create the Input object
    # We use model_dump() to convert the Pydantic object to a dict
    new_input = Input(**input_new.model_dump())
    db.add(new_input)
    
    # 3. Flush to generate the new_input.input_id without closing the transaction
    await db.flush()

    # 4. Create the link in the Junction Table
    new_link = PipelineInput(
        pipeline_id=pipeline_id,
        input_id=new_input.input_id
    )
    db.add(new_link)

    # 5. Commit everything properly
    await db.commit()
    await db.refresh(new_input)
    
    return new_input


# ------------------------------------------------------------------
# 2. LIST Inputs for a Pipeline
# GET /api/v1/{pipeline_id}/input
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/input", response_model=List[InputResponse])
async def read_inputs(
    pipeline_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all Inputs associated with a specific Pipeline.
    """
    # We must JOIN PipelineInput to filter by pipeline_id
    query = (
        select(Input)
        .join(PipelineInput, Input.input_id == PipelineInput.input_id)
        .where(PipelineInput.pipeline_id == pipeline_id)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------
# 3. GET ONE Input (Verified by Pipeline)
# GET /api/v1/{pipeline_id}/input/{input_id}
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/input/{input_id}", response_model=InputResponse)
async def read_input(
    pipeline_id: int, 
    input_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific input, ensuring it actually belongs to the pipeline.
    """
    query = (
        select(Input)
        .join(PipelineInput, Input.input_id == PipelineInput.input_id)
        .where(
            PipelineInput.pipeline_id == pipeline_id,
            Input.input_id == input_id
        )
    )
    
    result = await db.execute(query)
    input_obj = result.scalars().first()

    if not input_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Input not found or not associated with this pipeline"
        )

    return input_obj


# ------------------------------------------------------------------
# 4. UPDATE Input
# PUT /api/v1/{pipeline_id}/input/{input_id}
# ------------------------------------------------------------------
@router.put("/{pipeline_id}/input/{input_id}", response_model=InputResponse)
async def update_input(
    pipeline_id: int, 
    input_id: int, 
    input_update: InputUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Find the input (ensuring it belongs to the pipeline)
    query = (
        select(Input)
        .join(PipelineInput, Input.input_id == PipelineInput.input_id)
        .where(
            PipelineInput.pipeline_id == pipeline_id,
            Input.input_id == input_id
        )
    )
    result = await db.execute(query)
    input_obj = result.scalars().first()

    if not input_obj:
        raise HTTPException(status_code=404, detail="Input not found")

    # 2. Update fields
    # exclude_unset=True ensures we don't accidentally set fields to None 
    # if the user didn't send them in the JSON
    update_data = input_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(input_obj, key, value)

    # 3. Save
    db.add(input_obj)
    await db.commit()
    await db.refresh(input_obj)

    return input_obj


# ------------------------------------------------------------------
# 5. DELETE Input
# DELETE /api/v1/{pipeline_id}/input/{input_id}
# ------------------------------------------------------------------
@router.delete("/{pipeline_id}/input/{input_id}", status_code=status.HTTP_200_OK)
async def delete_input(
    pipeline_id: int, 
    input_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes the Input object entirely. 
    Note: Because of Cascade rules, this will also remove the link in PipelineInput.
    """
    # 1. Fetch the input
    query = (
        select(Input)
        .join(PipelineInput, Input.input_id == PipelineInput.input_id)
        .where(
            PipelineInput.pipeline_id == pipeline_id,
            Input.input_id == input_id
        )
    )
    result = await db.execute(query)
    input_obj = result.scalars().first()

    if not input_obj:
        raise HTTPException(status_code=404, detail="Input not found")

    # 2. Delete
    await db.delete(input_obj)
    await db.commit()

    return {"message": "Input deleted successfully", "input_id": input_id}