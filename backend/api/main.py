# main.py
import os
import json
import time
import docker 
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class PipelineInput(BaseModel):
    input_topic: str
    output_topic: str
    transformations: list[str]
    allow_producer: bool = False
    n_channels: int = 10
    frequency: float = 1.0

app = FastAPI(title="Pipeline Backend Docker Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # safer than "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def manage_pipeline_lifecycle(pipeline: PipelineInput):
    client = docker.from_env()
    
    # DEFINE PATHS
    # This matches the volume path in docker-compose
    path_to_worker_code = "/worker_code" 
    image_tag = os.environ.get("WORKER_IMAGE_NAME", "my-worker-image:latest")

    #BUILD THE IMAGE (This creates the container image from the folder)
    print("Building worker image...")
    client.images.build(
        path=path_to_worker_code, 
        tag=image_tag,
        rm=True
    )
    print("Build complete.")

    # RUN THE CONTAINER
    network_name = os.environ.get("DOCKER_NETWORK_NAME", "pipeline-backend-lite_redpanda_network")
    
    worker_env_vars = {
        "BROKER_ADDRESS": "redpanda:9092",
        "INPUT_TOPIC": pipeline.input_topic,
        "OUTPUT_TOPIC": pipeline.output_topic,
        "TRANSFORMATIONS": json.dumps(pipeline.transformations)
    }

    client.containers.run(
        image=image_tag,
        command=["python", "worker.py"],
        detach=True,
        network=network_name,
        environment=worker_env_vars,
        auto_remove=False
    )
    
@app.post("/start")
def process_data(pipeline: PipelineInput, background_tasks: BackgroundTasks):
    background_tasks.add_task(manage_pipeline_lifecycle, pipeline)
    return {"status": "accepted", "message": "Worker spawning initiated."}