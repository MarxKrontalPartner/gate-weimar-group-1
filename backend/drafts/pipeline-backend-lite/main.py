import sys, os, json, traceback, uuid, subprocess, time, socket
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

def start_redpanda_container(broker_address, yaml_file_path):
    try:
        if ":" in broker_address:
            host_ip, port = broker_address.split(":")
            port = int(port)
        else:
            host_ip = broker_address
            port = 19092 # the default

        # Prepare Environment Variables
        env_vars = os.environ.copy()
        env_vars["HOST_ADDRESS"] = host_ip 

        # Run Docker Compose (make sure your docker-compose.yaml is in the same folder or specify path)
        subprocess.run(
            ["docker", "compose", "-f", yaml_file_path, "up", "-d"], 
            check=True, 
            env=env_vars,
        )
        
        print("Docker container started. Waiting for Redpanda to be ready...")
        
        retries = 30
        while retries > 0:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host_ip, port))
            sock.close()
            
            if result == 0:
                print(f"Redpanda is ready at {broker_address}!")
                return
            
            time.sleep(1)
            retries -= 1
            if retries % 5 == 0: print("...still waiting for broker...")

        raise Exception("Timed out waiting for Redpanda to start.")
    
    except Exception as e:
        print(f"Failed to start Redpanda: {e}")
        raise e
    

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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    yaml_path = os.path.join(project_root, "broker", "docker-compose.yaml")

    start_redpanda_container(pipeline.address, yaml_path)

    quixApp = Application(
            broker_address=pipeline.address,
            auto_offset_reset="earliest",
            consumer_group=consumer_group,
        )
    input_topic = quixApp.topic(name = pipeline.input_topic)
    output_topic = quixApp.topic(name = pipeline.output_topic)
    current_dataframe = quixApp.dataframe(input_topic)

    for t_function in pipeline.transformations:
        transform_func = get_callable_function_for_transformation(t_function)
        current_dataframe = current_dataframe.apply(transform_func).filter(lambda x: x is not None)

    current_dataframe.to_topic(output_topic)
    quixApp.run()
    return "done"