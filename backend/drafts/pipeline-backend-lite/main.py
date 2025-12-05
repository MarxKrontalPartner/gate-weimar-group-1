import sys, os, json, traceback, uuid
from fastapi import FastAPI
from pydantic import BaseModel
from quixstreams import Application
from logger import get_logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Set a unique consumer group to avoid conflicts
consumer_group = f"consumer_group_{uuid.uuid4().hex[:8]}"

class PipelineInput(BaseModel):
    address: str
    input_topic: str
    output_topic: str
    transformations: list[str]

app = FastAPI(
    title="Pipeline Backend Lite",
    description="FastAPI service integrated with Quix Streams for data processing.",
    version="2.0.0"
)

def get_callable_function_for_transformation(transformation_script):
    
    local_scope = {}
    try:
        exec(transformation_script, {}, local_scope)
        return local_scope.get("transform", lambda x: x)
    except Exception as e:
        print(f"Script Error: {e}")
        return lambda x: x

@app.post("/start")
async def process_data(pipeline:PipelineInput):
    quixApp = Application(
            broker_address=pipeline.address,
            auto_offset_reset="earliest",
            consumer_group=consumer_group,
        )
    input_topic = quixApp.topic(name = pipeline.input_topic)
    output_topic = quixApp.topic(name = pipeline.output_topic)
    current_dataframe = app.dataframe(input_topic)

    for t_function in pipeline.transformations:
        transform_func = get_callable_function_for_transformation(t_function)
        current_dataframe = current_dataframe.apply(transform_func).filter(lambda x: x is not None)

    current_dataframe.to_topic(output_topic)
    return "done"