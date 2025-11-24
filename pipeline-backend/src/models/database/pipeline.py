from typing import TYPE_CHECKING, List

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.tag import PipelineTag
    from src.models.database.input import PipelineInput
    from src.models.database.output import PipelineOutput
    from src.models.database.transformation import PipelineTransformation
    from src.models.database.flow import PipelineFlow


class Pipeline(Base, TimestampMixin):
    """
    Pipeline model - represents a data processing pipeline.
    
    A pipeline is a collection of inputs, transformations, outputs,
    and flows that define how data is processed.
    """
    __tablename__ = "pipelines"
    
    pipeline_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    tags: Mapped[List["PipelineTag"]] = relationship(
        "PipelineTag",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    inputs: Mapped[List["PipelineInput"]] = relationship(
        "PipelineInput",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    outputs: Mapped[List["PipelineOutput"]] = relationship(
        "PipelineOutput",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    transformations: Mapped[List["PipelineTransformation"]] = relationship(
        "PipelineTransformation",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    flows: Mapped[List["PipelineFlow"]] = relationship(
        "PipelineFlow",
        back_populates="pipeline",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Pipeline(id={self.pipeline_id}, name='{self.name}')>"