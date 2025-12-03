from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.pipeline import Pipeline


class Output(Base, TimestampMixin):
    """
    Output model - represents a data destination (e.g., Kafka topic).
    
    Outputs define where processed data goes (topic, schema, broker).
    """
    __tablename__ = "outputs"
    
    output_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    schemas: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    broker_address: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Relationships
    pipelines: Mapped[List["PipelineOutput"]] = relationship(
        "PipelineOutput",
        back_populates="output",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Output(id={self.output_id}, name='{self.name}', topic='{self.topic}')>"


class PipelineOutput(Base, TimestampMixin):
    """
    Junction table linking Pipelines and Outputs (many-to-many relationship).
    
    A pipeline can have multiple outputs, and an output can be used by multiple pipelines.
    """
    __tablename__ = "pipeline_outputs"
    
    pipeline_output_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    output_id: Mapped[int] = mapped_column(
        ForeignKey("outputs.output_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="outputs")
    output: Mapped["Output"] = relationship("Output", back_populates="pipelines")
    
    def __repr__(self) -> str:
        return f"<PipelineOutput(pipeline_id={self.pipeline_id}, output_id={self.output_id})>"