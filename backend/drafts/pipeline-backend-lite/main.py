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
    """
    Spawns a sibling Docker container using the SAME image as this app.
    """
    # Connect to the Docker Daemon running on the host
    client = docker.from_env()

    # Identify the image to run. 
   
    image_name = os.environ.get("WORKER_IMAGE_NAME", "my-pipeline-image:latest")
    network_name = os.environ.get("DOCKER_NETWORK_NAME", "pipeline-backend-lite_redpanda_network")

    # Prepare Environment Variables for the worker
    worker_env_vars = {
        "BROKER_ADDRESS": "redpanda:9092", # Use internal Docker network name
        "INPUT_TOPIC": pipeline.input_topic,
        "OUTPUT_TOPIC": pipeline.output_topic,
        # Serialize the list of scripts into a JSON string
        "TRANSFORMATIONS": json.dumps(pipeline.transformations) 
    }

    producer_container = None
    worker_container = None
    try:
        print(f"Spawning container for {pipeline.input_topic}...")

        # --- Optional Producer ---
        if pipeline.allow_producer:
            print("allow_producer=True → Launching PRODUCER container...")

            producer_env = {
                "BROKER_ADDRESS": "redpanda:9092",
                "INPUT_TOPIC": pipeline.input_topic,
                "N_CHANNELS": str(pipeline.n_channels),
                "FREQUENCY": str(pipeline.frequency),
            }

            producer_container = client.containers.run(
                image=image_name,
                command=["python", "producer.py"],
                detach=True,
                network=network_name,
                environment=producer_env,
                auto_remove=True
            )
            print(f"Producer container {producer_container.short_id} started.")
        
        # Run the container
        worker_container = client.containers.run(
            image=image_name,
            command=["python", "worker.py"],
            detach=True,
            network=network_name,  
            environment=worker_env_vars,
            auto_remove=False # Change this to True if you want auto cleanup and avoid dangling containers
        )

        print(f"Container {worker_container.short_id} started. Running for 120s...")
        
        # Wait
        time.sleep(120)

        # Cleanup
        print(f"Time limit reached. Stopping container {worker_container.short_id}...")
        worker_container.stop()
        if pipeline.allow_producer:
            producer_container.stop()  

    except Exception as e:
        print(f"Lifecycle Manager failed: {e}")
        if worker_container:
            try:
                worker_container.stop()
            except:
                pass
            
        if producer_container:
            try:
                producer_container.stop()
            except:
                pass

@app.post("/start")
def process_data(pipeline: PipelineInput, background_tasks: BackgroundTasks):
    background_tasks.add_task(manage_pipeline_lifecycle, pipeline)
    return {"status": "accepted", "message": "Worker spawning initiated."}