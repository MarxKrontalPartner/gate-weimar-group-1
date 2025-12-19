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


    timestamp = int(time.time())
    container_name = f"consumer_{timestamp}_{timestamp}"
    

    worker_container =client.containers.run(
        image=image_tag,
        command=["python", "worker.py"],
        detach=True,
        network=network_name,
        environment=worker_env_vars,
        auto_remove=False,
        name=container_name
    )
    try:
        time.sleep(120)
        print(f"{worker_container.short_id} is running. Waiting 2 minutes")

    finally:
        print(f"Destroying container {worker_container.short_id}")
        try:
            worker_container.stop(timeout=10) # Give it 10s to shut down gracefully
            worker_container.remove(force=True) # Force removal to be safe
            print("Container destroyed.")
        except Exception as e:
            print(f"Error cleaning up container: {e}")


def run_pipelines_sequentially(pipelines: list[PipelineInput]):
    print(f"[BATCH] Received batch of {len(pipelines)} pipelines. Starting sequential execution...")
    
    for i, pipeline in enumerate(pipelines):
        print(f"[BATCH] Starting Pipeline {i+1}/{len(pipelines)}: {pipeline.input_topic}")
        manage_pipeline_lifecycle(pipeline)
        print(f"[BATCH] Finished Pipeline {i+1}/{len(pipelines)}")
    
    print("[BATCH] All pipelines in this request have finished.")

@app.post("/start")
def process_data(pipelines: list[PipelineInput], background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipelines_sequentially, pipelines)
    return {"status": "accepted", "message": f"{len(pipelines)} pipelines queued for sequential execution."}