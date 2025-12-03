from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.pipeline import Pipeline


class Tag(Base, TimestampMixin):
    """
    Tag model - represents a tag that can be applied to pipelines.
    
    Tags are used to categorize and filter pipelines.
    """
    __tablename__ = "tags"
    
    tag_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    
    # Relationships
    pipelines: Mapped[List["PipelineTag"]] = relationship(
        "PipelineTag",
        back_populates="tag",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Tag(id={self.tag_id}, name='{self.name}')>"


class PipelineTag(Base, TimestampMixin):
    """
    Junction table linking Pipelines and Tags (many-to-many relationship).
    
    A pipeline can have multiple tags, and a tag can be applied to multiple pipelines.
    """
    __tablename__ = "pipeline_tags"
    
    pipeline_tag_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.tag_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="pipelines")
    
    def __repr__(self) -> str:
        return f"<PipelineTag(pipeline_id={self.pipeline_id}, tag_id={self.tag_id})>"