# worker.py
import os
import json
import sys
import traceback
import uuid
import ast
from quixstreams import Application
from shared.logger import get_logger
from shared.events import emit_event

logger = get_logger("Worker")

def get_callable_function_for_transformation(idx, transformation_script):
    local_scope = {}
    try:
        tree = ast.parse(transformation_script)
        function_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                break
        if not function_name:
            raise ValueError("No function definition found in script.")
        
        exec(transformation_script, {}, local_scope)
        user_func = local_scope.get(function_name)
        
        if not user_func:
            raise ValueError(f"Function '{function_name}' not found or not callable after execution.")
        
        logger.info(f"Loaded transformation function: {function_name}")
        return user_func
    except Exception as e:
        logger.exception(f"Script compile error: {e}")
        emit_event(
            pipeline_id=PIPELINE_ID,
            segment_index=SEGMENT_INDEX,
            category="lifecycle",
            type="failed",
            data={
                "message": (
                    f"[ERROR] Worker crashed at Segment #{SEGMENT_INDEX+1}, "
                    f"Transformation #{idx+1}:\n\n{type(e).__name__}: {e}"
                ),
                "traceback": traceback.format_exc(),
            },
        )
        sys.exit(1)

def main():
    try:
        logger.info(
            f"Worker starting | input={input_topic_name} -> output={output_topic_name}"
        )
        logger.info(f"Loaded {len(transformations)} transformation(s)")

        # ------------------------------------
        # QUIX SETUP - Unique Consumer Group
        # ------------------------------------
        consumer_group = f"worker_{uuid.uuid4().hex[:8]}"
        
        app = Application(
            broker_address=broker_address,
            auto_offset_reset="earliest",
            consumer_group=consumer_group
        )

        input_topic = app.topic(input_topic_name, value_deserializer="json")
        output_topic = app.topic(output_topic_name, value_serializer="json")

        # Build DataFrame
        sdf = app.dataframe(input_topic)

        def handle_input(row):
            logger.info(f"INPUT ROW: {row}")

            # emit event to backend
            emit_event(
                pipeline_id=PIPELINE_ID,
                segment_index=SEGMENT_INDEX,
                category="stream",
                type="input",
                topic=input_topic_name,
                data=row,
            )
            return row

        sdf = sdf.update(handle_input)
        
        # --------------------
        # APPLY TRANSFORMATIONS
        # --------------------
        if not transformations:
            logger.info("No transformations provided — passing stream through unchanged")
        else:
            for idx, script in enumerate(transformations):
                logger.info(f"Applying transformation #{idx+1}")
                func = get_callable_function_for_transformation(idx, script)
                def safe_func(row, func=func, idx=idx):
                    try:
                        return func(row)
                    except Exception as e:
                        logger.exception(f"Error in transformation #{idx+1}: {e}")
                        emit_event(
                            pipeline_id=PIPELINE_ID,
                            segment_index=SEGMENT_INDEX,
                            category="lifecycle",
                            type="failed",
                            data={
                                "message": (
                                    f"[ERROR] Worker crashed at Segment #{SEGMENT_INDEX+1}, "
                                    f"Transformation #{idx+1}:\n\n{type(e).__name__}: {e}"
                                ),
                                "traceback": traceback.format_exc(),
                            },
                        )
                        sys.exit(1)
                sdf = sdf.apply(safe_func).filter(lambda x: x is not None)

        def handle_output(row):
            logger.info(f"OUTPUT ROW: {row}")

            # emit event to backend
            emit_event(
                pipeline_id=PIPELINE_ID,
                segment_index=SEGMENT_INDEX,
                category="stream",
                type="output",
                topic=output_topic_name,
                data=row,
            )
            return row

        sdf = sdf.apply(handle_output)    
        sdf.to_topic(output_topic)

        logger.info("Worker pipeline initialized — running")
        app.run()

    except Exception as e:
        logger.error(f"Worker crashed with fatal error: {e}")
        logger.error(traceback.format_exc())
        emit_event(
            pipeline_id=PIPELINE_ID,
            segment_index=SEGMENT_INDEX,
            category="lifecycle",
            type="failed",
            data={
                "message": f"[ERROR] Worker crashed:\n\n{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            },
        )
        sys.exit(1)

if __name__ == "__main__":
    # --------------------
    # ENV CONFIG
    # --------------------
    PIPELINE_ID = os.environ["PIPELINE_ID"]
    SEGMENT_INDEX = int(os.environ.get("SEGMENT_INDEX", "0"))
    broker_address = os.environ.get("BROKER_ADDRESS", "redpanda:9092")
    input_topic_name = os.environ["INPUT_TOPIC"]
    output_topic_name = os.environ["OUTPUT_TOPIC"]
    transformations = json.loads(os.environ.get("TRANSFORMATIONS", "[]"))
    main()