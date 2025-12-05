import sys, os, json, traceback, uuid, subprocess, time, socket
import multiprocessing  
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from quixstreams import Application
from logger import get_logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

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

# --- HELPER FUNCTIONS ---

def start_redpanda_container(broker_address, yaml_file_path):
  
    try:
        if ":" in broker_address:
            host_ip, port = broker_address.split(":")
            port = int(port)
        else:
            host_ip = broker_address
            port = 19092 

        # Quick Check if it already open?
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        if sock.connect_ex((host_ip, port)) == 0:
            sock.close()
            return # Already running, save time

        # Start Docker
        env_vars = os.environ.copy()
        env_vars["HOST_ADDRESS"] = host_ip 

        subprocess.run(
            ["docker", "compose", "-f", yaml_file_path, "up", "-d"], 
            check=True, 
            env=env_vars,
        )
        
        print("Docker container started. Waiting for Redpanda to be ready...")
        
        # Wait for readiness
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

        raise Exception("Timed out waiting for Redpanda.")
    
    except Exception as e:
        print(f"Failed to start Redpanda: {e}")
        raise e

def get_callable_function_for_transformation(transformation_script):
    
    local_scope = {}
    try:
        exec(transformation_script, {}, local_scope)
        user_func = local_scope.get("transform")
        if not user_func: return lambda x: x

    except Exception as e:
        print(f"Script Compile Error: {e}")
        return lambda x: x

# --- THE WORKER PROCESS ---

def _run_quix_process(pipeline: PipelineInput):
    """
    This function runs in a completely separate process.
    It has its own Main Thread, so Quix signals will work normally.
    """
    logger = get_logger(__name__)
    logger.info(f"Worker Process Started for {pipeline.input_topic}")
    
    try:
       
        d_consumer_group = f"consumer_group_{uuid.uuid4().hex[:8]}"
        
        quixApp = Application(
            broker_address=pipeline.address,
            auto_offset_reset="earliest",
            consumer_group=d_consumer_group
        )

        input_topic = quixApp.topic(pipeline.input_topic, value_deserializer="json")
        output_topic = quixApp.topic(pipeline.output_topic, value_serializer="json")

        #  Build DataFrame
        df = quixApp.dataframe(input_topic)
        for script in pipeline.transformations:
            func = get_callable_function_for_transformation(script)
            df = df.apply(func).filter(lambda x: x is not None)
        df.to_topic(output_topic)

        #  Run (Blocks forever until process is killed)
        logger.info("Quix App running...")
        quixApp.run()
    
    except Exception as e:
        logger.error(f"Worker Process Crashed: {traceback.format_exc()}")

# --- THE MANAGER (Runs in BackgroundTasks) ---

def manage_pipeline_lifecycle(pipeline: PipelineInput):
    """
    Spawns the worker, waits 59s, then kills it.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    yaml_path = os.path.join(project_root, "broker", "docker-compose.yaml")

    # Ensure infra is up before spawning
    start_redpanda_container(pipeline.address, yaml_path)

    # Spawn the independent process
    
    p = multiprocessing.Process(target=_run_quix_process, args=(pipeline,))
    p.start()
    
    print(f"Pipeline started (PID: {p.pid}). Running for 59s...")
    
    # Wait
    time.sleep(59)
    
    # Cleanup
    print(f"Time limit reached. Terminating PID {p.pid}...")
    p.terminate() 
    p.join()
    print("Pipeline terminated successfully.")



@app.post("/start")
def process_data(pipeline: PipelineInput, background_tasks: BackgroundTasks):
    # Hand off to the manager
    background_tasks.add_task(manage_pipeline_lifecycle, pipeline)
    
    return {
        "status": "accepted", 
        "message": "Pipeline processing started.", 
        "details": f"Listening on {pipeline.input_topic}"
    }