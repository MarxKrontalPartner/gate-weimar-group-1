from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.pipeline import Pipeline


class Transformation(Base, TimestampMixin):
    """
    Transformation model - represents a data transformation step.
    
    Transformations contain the logic (Python script) that processes data
    from one schema to another.
    """
    __tablename__ = "transformations"
    
    transformation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_in: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    schema_out: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    python_script: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    pipelines: Mapped[List["PipelineTransformation"]] = relationship(
        "PipelineTransformation",
        back_populates="transformation",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Transformation(id={self.transformation_id}, name='{self.name}')>"


class PipelineTransformation(Base, TimestampMixin):
    """
    Junction table linking Pipelines and Transformations (many-to-many relationship).
    
    A pipeline can have multiple transformations, and a transformation can be
    reused across multiple pipelines.
    """
    __tablename__ = "pipeline_transformations"
    
    pipeline_transformation_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transformation_id: Mapped[int] = mapped_column(
        ForeignKey("transformations.transformation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="transformations")
    transformation: Mapped["Transformation"] = relationship(
        "Transformation",
        back_populates="pipelines",
    )
    
    def __repr__(self) -> str:
        return (
            f"<PipelineTransformation(pipeline_id={self.pipeline_id}, "
            f"transformation_id={self.transformation_id})>"
        )
    