# main.py
import os
import json
import time
import docker 
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

class PipelineInput(BaseModel):
    address: str
    input_topic: str
    output_topic: str
    transformations: list[str]

app = FastAPI(title="Pipeline Backend Docker Manager")

def manage_pipeline_lifecycle(pipeline: PipelineInput):
    """
    Spawns a sibling Docker container using the SAME image as this app.
    """
    # Connect to the Docker Daemon running on the host
    client = docker.from_env()

    # 1. Identify the image to run. 
    # In a real setup, you pass this via ENV, e.g., "my-pipeline-app:latest"
    image_name = os.environ.get("WORKER_IMAGE_NAME", "my-pipeline-image:latest")
    network_name = os.environ.get("DOCKER_NETWORK_NAME", "pipeline-backend-lite_redpanda_network")

    # 2. Prepare Environment Variables for the worker
    env_vars = {
        "BROKER_ADDRESS": "redpanda:9092", # Use internal Docker network name
        "INPUT_TOPIC": pipeline.input_topic,
        "OUTPUT_TOPIC": pipeline.output_topic,
        # Serialize the list of scripts into a JSON string
        "TRANSFORMATIONS": json.dumps(pipeline.transformations) 
    }

    container = None
    try:
        print(f"Spawning container for {pipeline.input_topic}...")
        
        # 3. Run the container
        container = client.containers.run(
            image=image_name,
            command=["python", "worker.py"],
            detach=True,
            network=network_name,  # <--- Uses the variable now
            environment=env_vars,
            auto_remove=False
        )

        print(f"Container {container.short_id} started. Running for 59s...")
        
        # 4. Wait
        time.sleep(59)

        # 5. Cleanup
        print(f"Time limit reached. Stopping container {container.short_id}...")
        container.stop() 

    except Exception as e:
        print(f"Lifecycle Manager failed: {e}")
        if container:
            try:
                container.stop()
            except:
                pass

@app.post("/start")
def process_data(pipeline: PipelineInput, background_tasks: BackgroundTasks):
    background_tasks.add_task(manage_pipeline_lifecycle, pipeline)
    return {"status": "accepted", "message": "Worker spawning initiated."}