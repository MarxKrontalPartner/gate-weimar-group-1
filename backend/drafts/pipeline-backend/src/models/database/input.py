from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.pipeline import Pipeline


class Input(Base, TimestampMixin):
    """
    Input model - represents a data source (e.g., Kafka topic).
    
    Inputs define where data comes from (topic, schema, broker).
    """
    __tablename__ = "inputs"
    
    input_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    schemas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    broker_address: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Relationships
    pipelines: Mapped[List["PipelineInput"]] = relationship(
        "PipelineInput",
        back_populates="input",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Input(id={self.input_id}, name='{self.name}', topic='{self.topic}')>"


class PipelineInput(Base, TimestampMixin):
    """
    Junction table linking Pipelines and Inputs (many-to-many relationship).
    
    A pipeline can have multiple inputs, and an input can be used by multiple pipelines.
    """
    __tablename__ = "pipeline_inputs"
    
    pipeline_input_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_id: Mapped[int] = mapped_column(
        ForeignKey("inputs.input_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="inputs")
    input: Mapped["Input"] = relationship("Input", back_populates="pipelines")
    
    def __repr__(self) -> str:
        return f"<PipelineInput(pipeline_id={self.pipeline_id}, input_id={self.input_id})>"