from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.database.pipeline import Pipeline


class NodeType(str, enum.Enum):
    """
    Enum defining the types of nodes in a flow.
    
    A flow connects nodes, which can be inputs, outputs, or transformations.
    """
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORMATION = "transformation"


class Flow(Base, TimestampMixin):
    """
    Flow model - represents a connection between two nodes in a pipeline.
    
    Flows define the data flow: where data comes from (start_node)
    and where it goes (end_node).
    
    Example:
    - Input "user_events" -> Transformation "clean_data"
    - Transformation "clean_data" -> Output "processed_events"
    """
    __tablename__ = "flows"
    
    flow_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    start_node_type: Mapped[NodeType] = mapped_column(
        SQLEnum(NodeType, name="node_type", native_enum=False),
        nullable=False,
    )
    end_node_type: Mapped[NodeType] = mapped_column(
        SQLEnum(NodeType, name="node_type", native_enum=False),
        nullable=False,
    )
    start_node: Mapped[int] = mapped_column(nullable=False)
    end_node: Mapped[int] = mapped_column(nullable=False)
    
    # Relationships
    pipelines: Mapped[List["PipelineFlow"]] = relationship(
        "PipelineFlow",
        back_populates="flow",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return (
            f"<Flow(id={self.flow_id}, "
            f"{self.start_node_type.value}:{self.start_node} -> "
            f"{self.end_node_type.value}:{self.end_node})>"
        )


class PipelineFlow(Base, TimestampMixin):
    """
    Junction table linking Pipelines and Flows (many-to-many relationship).
    
    A pipeline can have multiple flows, and a flow can be reused
    across multiple pipelines.
    """
    __tablename__ = "pipeline_flows"
    
    pipeline_flow_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("pipelines.pipeline_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flow_id: Mapped[int] = mapped_column(
        ForeignKey("flows.flow_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="flows")
    flow: Mapped["Flow"] = relationship("Flow", back_populates="pipelines")
    
    def __repr__(self) -> str:
        return f"<PipelineFlow(pipeline_id={self.pipeline_id}, flow_id={self.flow_id})>"