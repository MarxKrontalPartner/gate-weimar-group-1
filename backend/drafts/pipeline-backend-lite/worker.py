# worker.py
import os
import json
import traceback
import uuid
import ast
from quixstreams import Application
import requests

FASTAPI_EVENT_ENDPOINT = "http://pipeline-manager:8000/stream/event"

def emit_event(event_type, topic, data):
    try:
        requests.post(
            FASTAPI_EVENT_ENDPOINT,
            json={
                "type": event_type,
                "topic": topic,
                "data": data
            },
            timeout=0.2  # non-blocking-ish
        )
    except Exception:
        # UI should NEVER be able to crash the pipeline
        pass

def get_callable_function_for_transformation(transformation_script):
    local_scope = {}
    try:
        tree = ast.parse(transformation_script)
        function_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                break
        if not function_name:
            print("Error: No function definition found in script.")
            return lambda x: x
        
        exec(transformation_script, {}, local_scope)
        user_func = local_scope.get(function_name)
        
        if not user_func: return lambda x: x
        return user_func
    except Exception as e:
        print(f"Script Compile Error: {e}")
        return lambda x: x

def main():
    try:
        # Load Config from Env Vars (injected by main.py)
        broker_address = os.environ.get("BROKER_ADDRESS", "redpanda:9092")
        input_topic_name = os.environ["INPUT_TOPIC"]
        output_topic_name = os.environ["OUTPUT_TOPIC"]
        
        # We pass the list of scripts as a JSON string
        transformations_json = os.environ.get("TRANSFORMATIONS", "[]")
        transformations = json.loads(transformations_json)

        print(f"WORKER STARTED: {input_topic_name} -> {output_topic_name}")

        # Setup Quix
        # Create a unique consumer group to ensure we don't conflict with previous runs
        c_group = f"worker_{uuid.uuid4().hex[:8]}"
        
        app = Application(
            broker_address=broker_address,
            auto_offset_reset="earliest",
            consumer_group=c_group
        )

        input_topic = app.topic(input_topic_name, value_deserializer="json")
        output_topic = app.topic(output_topic_name, value_serializer="json")

        # Build DataFrame
        sdf = app.dataframe(input_topic)

        # This will print every message receiving from Kafka to the logs
        # sdf = sdf.update(lambda row: print(f"DEBUG INPUT: {row}"))

        def handle_input(row):
            print(f"DEBUG INPUT: {row}")
            emit_event("input", input_topic_name, row)
            return row

        sdf = sdf.update(handle_input)
        
        for script in transformations:
            func = get_callable_function_for_transformation(script)
            sdf = sdf.apply(func).filter(lambda x: x is not None)
        
        def handle_output(row):
            emit_event("output", output_topic_name, row)
            return row

        sdf = sdf.apply(handle_output)
            
        sdf.to_topic(output_topic)

        # Run
        app.run()

    except Exception as e:
        print(f"Worker Crashed: {traceback.format_exc()}")

if __name__ == "__main__":
    main()