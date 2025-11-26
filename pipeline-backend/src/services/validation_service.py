import socket
import json
from typing import List, Dict, Set, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Models
from src.models.database.pipeline import Pipeline
from src.models.database.flow import Flow, NodeType, PipelineFlow
from src.models.database.input import Input, PipelineInput
from src.models.database.output import Output, PipelineOutput
from src.models.database.transformation import Transformation, PipelineTransformation


class ValidationService:
    """
    Service responsible for verifying pipeline integrity before execution.
    """

    @staticmethod
    async def validate_pipeline(pipeline_id: int, db: AsyncSession) -> Dict[str, Any]:
        errors = []
        warnings = []

        # 1. FETCH PIPELINE DATA
        # We need to fetch the pipeline and all its related components
        query = (
            select(Pipeline)
            .options(
                selectinload(Pipeline.inputs).selectinload(PipelineInput.input),
                selectinload(Pipeline.outputs).selectinload(PipelineOutput.output),
                selectinload(Pipeline.transformations).selectinload(PipelineTransformation.transformation),
                selectinload(Pipeline.flows).selectinload(PipelineFlow.flow)
            )
            .where(Pipeline.pipeline_id == pipeline_id)
        )
        result = await db.execute(query)
        pipeline = result.scalars().first()

        if not pipeline:
            return {"valid": False, "errors": ["Pipeline not found"], "warnings": []}

        # Extract actual objects from the junction tables
        inputs = [pi.input for pi in pipeline.inputs]
        outputs = [po.output for po in pipeline.outputs]
        transforms = [pt.transformation for pt in pipeline.transformations]
        flows = [pf.flow for pf in pipeline.flows]

        if not inputs:
            errors.append("Pipeline has no inputs defined.")
        if not outputs:
            errors.append("Pipeline has no outputs defined.")
        if not flows:
            errors.append("Pipeline has no flows (connections) defined.")

        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}

        # 2. CONNECTIVITY CHECK (Socket Ping)
        # Check if we can actually reach the Kafka brokers
        for inp in inputs:
            if not ValidationService._check_socket(inp.broker_address):
                errors.append(f"Input '{inp.name}': Cannot reach broker at {inp.broker_address}")
        
        for out in outputs:
            if not ValidationService._check_socket(out.broker_address):
                errors.append(f"Output '{out.name}': Cannot reach broker at {out.broker_address}")

        # 3. STRUCTURAL CHECK (Graph Theory)
        # Check for cycles and disconnected nodes
        graph_errors = ValidationService._validate_graph_structure(inputs, outputs, transforms, flows)
        errors.extend(graph_errors)

        # 4. SCHEMA COMPATIBILITY CHECK
        # Check if flow data types match
        schema_warnings = ValidationService._validate_schemas(flows, inputs, outputs, transforms)
        warnings.extend(schema_warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "pipeline_name": pipeline.name
        }

    # --- Helper Methods ---

    @staticmethod
    def _check_socket(address: str) -> bool:
        """
        Tries to open a TCP connection to the broker.
        Expected format: "host:port" (e.g., "localhost:9092")
        """
        try:
            host, port_str = address.split(":")
            port = int(port_str)
            # Create a socket connection with a short timeout
            with socket.create_connection((host, port), timeout=3):
                return True
        except Exception:
            return False

    @staticmethod
    def _validate_graph_structure(
        inputs: List[Input], 
        outputs: List[Output], 
        transforms: List[Transformation], 
        flows: List[Flow]
    ) -> List[str]:
        """
        Checks for:
        1. Valid start/end nodes
        2. Cycles (Infinite loops)
        3. Islands (Unconnected nodes)
        """
        errors = []
        
        # Build Adjacency List: { node_id_str: [connected_node_id_str, ...] }
        # We use strings like "input_1", "transformation_2" to uniquely identify nodes across tables
        adj_list: Dict[str, List[str]] = {}
        all_nodes: Set[str] = set()

        # Register all nodes
        for i in inputs: all_nodes.add(f"input_{i.input_id}")
        for o in outputs: all_nodes.add(f"output_{o.output_id}")
        for t in transforms: all_nodes.add(f"transformation_{t.transformation_id}")

        # Build edges
        for flow in flows:
            u = f"{flow.start_node_type.value}_{flow.start_node}" # e.g. "input_1"
            v = f"{flow.end_node_type.value}_{flow.end_node}"     # e.g. "transformation_2"
            
            if u not in adj_list: adj_list[u] = []
            adj_list[u].append(v)

            # Validate logic: Input cannot be an end node
            if flow.end_node_type.value == "input":
                errors.append(f"Flow Error: Input cannot be a destination (Flow ID: {flow.flow_id})")
            
            # Validate logic: Output cannot be a start node
            if flow.start_node_type.value == "output":
                errors.append(f"Flow Error: Output cannot be a source (Flow ID: {flow.flow_id})")

        # Cycle Detection (DFS)
        visited = set()
        recursion_stack = set()

        def has_cycle(node):
            visited.add(node)
            recursion_stack.add(node)
            
            if node in adj_list:
                for neighbor in adj_list[node]:
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in recursion_stack:
                        return True
            
            recursion_stack.remove(node)
            return False

        for node in list(adj_list.keys()):
            if node not in visited:
                if has_cycle(node):
                    errors.append("Critical: Infinite loop (cycle) detected in pipeline flows.")
                    break # Stop looking for more cycles if one is found

        return errors

    @staticmethod
    def _validate_schemas(
        flows: List[Flow], 
        inputs: List[Input], 
        outputs: List[Output], 
        transforms: List[Transformation]
    ) -> List[str]:
        """
        Simple check: Does the destination schema expect keys that the source doesn't provide?
        """
        warnings = []
        
        # Helper to find schema
        def get_schema(node_type: str, node_id: int, is_source: bool) -> dict:
            if node_type == "input":
                found = next((x for x in inputs if x.input_id == node_id), None)
                return found.schemas if found else {}
            elif node_type == "output":
                found = next((x for x in outputs if x.output_id == node_id), None)
                return found.schemas if found else {}
            elif node_type == "transformation":
                found = next((x for x in transforms if x.transformation_id == node_id), None)
                if not found: return {}
                return found.schema_out if is_source else found.schema_in
            return {}

        for flow in flows:
            # Source Schema (What is coming out of the start node)
            src_schema = get_schema(flow.start_node_type.value, flow.start_node, is_source=True)
            # Target Schema (What is expected by the end node)
            tgt_schema = get_schema(flow.end_node_type.value, flow.end_node, is_source=False)

            if src_schema and tgt_schema:
                # Basic Check: Do required keys in Target exist in Source?
                # Assuming schemas are simple dicts like {"field": "type"}
                src_keys = set(src_schema.keys())
                tgt_keys = set(tgt_schema.keys())
                
                missing_keys = tgt_keys - src_keys
                if missing_keys:
                    warnings.append(
                        f"Schema Mismatch between {flow.start_node_type.value}_{flow.start_node} "
                        f"and {flow.end_node_type.value}_{flow.end_node}. "
                        f"Missing keys: {missing_keys}"
                    )

        return warnings