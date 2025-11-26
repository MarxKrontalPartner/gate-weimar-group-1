from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Import Dependency
from src.api.deps import get_db

# Import Models
from src.models.database.tag import Tag, PipelineTag
from src.models.database.pipeline import Pipeline

# Import Schemas
from src.schemas.tag import TagCreate, TagResponse

router = APIRouter()

# ------------------------------------------------------------------
# 1. ADD Tag to Pipeline (Find or Create)
# POST /api/v1/pipeline/{pipeline_id}/tag
# ------------------------------------------------------------------
@router.post("/{pipeline_id}/tag", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def add_tag_to_pipeline(
    pipeline_id: int, 
    tag_in: TagCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Add a tag to a pipeline. 
    Logic: 
    1. If tag exists by name, use it. 
    2. If not, create it.
    3. Link it to the pipeline (if not already linked).
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

    # 2. Check if Tag exists globally (Reuse tags)
    tag_query = select(Tag).where(Tag.name == tag_in.name)
    tag_result = await db.execute(tag_query)
    tag_obj = tag_result.scalars().first()

    # 3. Create Tag if it doesn't exist
    if not tag_obj:
        tag_obj = Tag(name=tag_in.name)
        db.add(tag_obj)
        await db.flush() # Generate ID

    # 4. Check if Link already exists (Prevent duplicate tagging)
    link_query = select(PipelineTag).where(
        PipelineTag.pipeline_id == pipeline_id,
        PipelineTag.tag_id == tag_obj.tag_id
    )
    link_result = await db.execute(link_query)
    existing_link = link_result.scalars().first()

    # 5. Create Link if not exists
    if not existing_link:
        new_link = PipelineTag(
            pipeline_id=pipeline_id,
            tag_id=tag_obj.tag_id
        )
        db.add(new_link)
        await db.commit()
    else:
        # If link exists, we just commit the transaction to ensure the tag creation (if any) persists
        # But we don't error out, we just return the tag.
        await db.commit()

    await db.refresh(tag_obj)
    return tag_obj


# ------------------------------------------------------------------
# 2. LIST Tags for a Pipeline
# GET /api/v1/pipeline/{pipeline_id}/tag
# ------------------------------------------------------------------
@router.get("/{pipeline_id}/tag", response_model=List[TagResponse])
async def read_tags(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Get all Tags associated with a specific Pipeline.
    """
    query = (
        select(Tag)
        .join(PipelineTag, Tag.tag_id == PipelineTag.tag_id)
        .where(PipelineTag.pipeline_id == pipeline_id)
    )
    
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------
# 3. REMOVE Tag from Pipeline
# DELETE /api/v1/pipeline/{pipeline_id}/tag/{tag_id}
# ------------------------------------------------------------------
@router.delete("/{pipeline_id}/tag/{tag_id}", status_code=status.HTTP_200_OK)
async def remove_tag_from_pipeline(
    pipeline_id: int, 
    tag_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a tag from a pipeline (Unlink).
    Does NOT delete the tag itself, as it might be used by other pipelines.
    """
    # 1. Find the Link
    query = select(PipelineTag).where(
        PipelineTag.pipeline_id == pipeline_id,
        PipelineTag.tag_id == tag_id
    )
    result = await db.execute(query)
    link_obj = result.scalars().first()

    if not link_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tag not attached to this pipeline"
        )

    # 2. Delete the Link
    await db.delete(link_obj)
    await db.commit()

    return {"message": "Tag removed from pipeline", "tag_id": tag_id}