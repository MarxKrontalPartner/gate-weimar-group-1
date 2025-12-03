from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.transformation import Transformation, PipelineTransformation
from src.models.database.pipeline import Pipeline

# Import Schemas
from src.schemas.transformation import (
    TransformationCreate, 
    TransformationResponse, 
    TransformationUpdate
)

router = APIRouter()

# ------------------------------------------------------------------
# 1. CREATE Transformation & Link to Pipeline
# POST /api/v1/pipeline/{pipeline_id}/transformation
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/transformation", response_model=TransformationResponse, status_code=status.HTTP_201_CREATED)
async def create_transformation_for_pipeline(
    pipeline_id: int, 
    transformation_in: TransformationCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Transformation logic block and link it to the Pipeline.
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

    # 2. Create the Transformation object
    new_transform = Transformation(**transformation_in.model_dump())
    db.add(new_transform)
    
    # 3. Flush to generate the ID
    await db.flush()

    # 4. Create the link in the Junction Table
    new_link = PipelineTransformation(
        pipeline_id=pipeline_id,
        transformation_id=new_transform.transformation_id
    )
    db.add(new_link)

    # 5. Commit
    await db.commit()
    await db.refresh(new_transform)
    
    return new_transform


# ------------------------------------------------------------------
# 2. LIST Transformations for a Pipeline
# GET /api/v1/pipeline/{pipeline_id}/transformation
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/transformation", response_model=List[TransformationResponse])
async def read_transformations(
    pipeline_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all Transformations associated with a specific Pipeline.
    """
    query = (
        select(Transformation)
        .join(PipelineTransformation, Transformation.transformation_id == PipelineTransformation.transformation_id)
        .where(PipelineTransformation.pipeline_id == pipeline_id)
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------
# 3. GET ONE Transformation (Verified by Pipeline)
# GET /api/v1/pipeline/{pipeline_id}/transformation/{transformation_id}
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/transformation/{transformation_id}", response_model=TransformationResponse)
async def read_transformation(
    pipeline_id: int, 
    transformation_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific transformation, ensuring it actually belongs to the pipeline.
    """
    query = (
        select(Transformation)
        .join(PipelineTransformation, Transformation.transformation_id == PipelineTransformation.transformation_id)
        .where(
            PipelineTransformation.pipeline_id == pipeline_id,
            Transformation.transformation_id == transformation_id
        )
    )
    
    result = await db.execute(query)
    transform_obj = result.scalars().first()

    if not transform_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Transformation not found or not associated with this pipeline"
        )

    return transform_obj


# ------------------------------------------------------------------
# 4. UPDATE Transformation
# PUT /api/v1/pipeline/{pipeline_id}/transformation/{transformation_id}
# ------------------------------------------------------------------
@router.put("/{pipeline_id}/transformation/{transformation_id}", response_model=TransformationResponse)
async def update_transformation(
    pipeline_id: int, 
    transformation_id: int, 
    transform_update: TransformationUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Find the transformation
    query = (
        select(Transformation)
        .join(PipelineTransformation, Transformation.transformation_id == PipelineTransformation.transformation_id)
        .where(
            PipelineTransformation.pipeline_id == pipeline_id,
            Transformation.transformation_id == transformation_id
        )
    )
    result = await db.execute(query)
    transform_obj = result.scalars().first()

    if not transform_obj:
        raise HTTPException(status_code=404, detail="Transformation not found")

    # 2. Update fields
    update_data = transform_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(transform_obj, key, value)

    # 3. Save
    db.add(transform_obj)
    await db.commit()
    await db.refresh(transform_obj)

    return transform_obj


# ------------------------------------------------------------------
# 5. DELETE Transformation
# DELETE /api/v1/pipeline/{pipeline_id}/transformation/{transformation_id}
# ------------------------------------------------------------------
@router.delete("/{pipeline_id}/transformation/{transformation_id}", status_code=status.HTTP_200_OK)
async def delete_transformation(
    pipeline_id: int, 
    transformation_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes the Transformation object.
    """
    # 1. Fetch
    query = (
        select(Transformation)
        .join(PipelineTransformation, Transformation.transformation_id == PipelineTransformation.transformation_id)
        .where(
            PipelineTransformation.pipeline_id == pipeline_id,
            Transformation.transformation_id == transformation_id
        )
    )
    result = await db.execute(query)
    transform_obj = result.scalars().first()

    if not transform_obj:
        raise HTTPException(status_code=404, detail="Transformation not found")

    # 2. Delete
    await db.delete(transform_obj)
    await db.commit()

    return {"message": "Transformation deleted successfully", "transformation_id": transformation_id}