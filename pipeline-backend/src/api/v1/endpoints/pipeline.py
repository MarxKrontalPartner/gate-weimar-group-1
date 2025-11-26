from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

# Import the get_db dependency
from src.api.deps import get_db
# Import Models
from src.models.database.pipeline import Pipeline
from src.models.database.tag import Tag
# Import Schemas
from src.schemas.pipeline import PipelineCreate, PipelineResponse, PipelineUpdate

router = APIRouter()

# --- 1. CREATE (POST) ---
@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    pipeline_in: PipelineCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Create a new pipeline with optional tags."""
    # Check if name exists
    result = await db.execute(select(Pipeline).where(Pipeline.name == pipeline_in.name))
    existing_pipeline = result.scalars().first()
    
    if existing_pipeline:
        raise HTTPException(
            status_code=400, 
            detail="A pipeline with this name already exists."
        )

    # Create Pipeline
    new_pipeline = Pipeline(
        name=pipeline_in.name,
        description=pipeline_in.description,
    )

    db.add(new_pipeline)
    await db.commit()
    # Refresh with tags loaded
    await db.refresh(new_pipeline, ["tags"])
    return new_pipeline

# --- 2. LIST ALL (GET) ---
@router.get("", response_model=List[PipelineResponse])
async def read_pipelines(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all pipelines."""
    # selectinload(Pipeline.tags) ensures tags are fetched efficiently
    query = select(Pipeline).options(selectinload(Pipeline.tags)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

# --- 3. GET ONE (GET /{id}) ---
@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def read_pipeline(
    pipeline_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve a specific pipeline by ID."""
    query = select(Pipeline).options(selectinload(Pipeline.tags)).where(Pipeline.pipeline_id == pipeline_id)
    result = await db.execute(query)
    pipeline = result.scalars().first()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline

# --- 4. UPDATE (PUT /{id}) ---
@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: int,
    pipeline_in: PipelineUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a pipeline."""
    # Fetch existing pipeline
    query = select(Pipeline).options(selectinload(Pipeline.tags)).where(Pipeline.pipeline_id == pipeline_id)
    result = await db.execute(query)
    pipeline = result.scalars().first()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Update basic fields if provided
    if pipeline_in.name is not None:
        pipeline.name = pipeline_in.name
    if pipeline_in.description is not None:
        pipeline.description = pipeline_in.description

    # Update tags if provided
    if pipeline_in.tags is not None:
        tag_objects = []
        for tag_name in pipeline_in.tags:
            result = await db.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalars().first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.commit()
                await db.refresh(tag)
            tag_objects.append(tag)
        # Replace old tags with new list
        pipeline.tags = tag_objects

    await db.commit()
    await db.refresh(pipeline)
    return pipeline

# --- 5. DELETE (DELETE /{id}) ---
@router.delete("/{pipeline_id}", status_code=status.HTTP_200_OK)
async def delete_pipeline(
    pipeline_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a pipeline."""
    query = select(Pipeline).where(Pipeline.pipeline_id == pipeline_id)
    result = await db.execute(query)
    pipeline = result.scalars().first()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    await db.delete(pipeline)
    await db.commit()
    return {"message": "Pipeline deleted successfully", "pipeline_id": pipeline_id}