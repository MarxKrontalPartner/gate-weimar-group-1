import multiprocessing
import threading
import logging
import traceback
import json
import signal
from typing import Dict, Any, List
from datetime import datetime

from quixstreams import Application
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models.database.pipeline import Pipeline
from src.models.database.flow import PipelineFlow
from src.models.database.input import PipelineInput
from src.models.database.output import PipelineOutput
from src.models.database.transformation import PipelineTransformation

logger = logging.getLogger(__name__)

class QuixPipelineManager:
    _instance = None
    _active_pipelines: Dict[int, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QuixPipelineManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_status(cls, pipeline_id: int) -> Dict[str, Any]:
        if pipeline_id in cls._active_pipelines:
            ctx = cls._active_pipelines[pipeline_id]
            process = ctx["process"]
            status = "running" if process.is_alive() else "stopped"
            if process.exitcode is not None and process.exitcode != 0:
                status = "failed"
            return {"status": status, "uptime": "N/A", "details": {"pid": process.pid}}
        return {"status": "stopped", "uptime": "0s", "details": None}

    @classmethod
    async def start_pipeline(cls, pipeline_id: int, db: AsyncSession):
        try:
            if pipeline_id in cls._active_pipelines and cls._active_pipelines[pipeline_id]["process"].is_alive():
                raise ValueError("Pipeline is already running.")

            # construct pipeline
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
                raise ValueError("Pipeline not found.")

            print(f"DEBUG: Pipeline fetched: {pipeline.pipeline_id}")

            # Prepare Configuration
            config = {
                "pipeline_id": pipeline.pipeline_id,
                "group_id_prefix": f"pipeline-{pipeline.pipeline_id}",
                "inputs": {},
                "outputs": {},
                "transformations": {},
                "flows": []
            }

            # Helper to fix localhost for Docker
            def fix_broker(addr):
                if "localhost" in addr:
                    return addr.replace("localhost", "host.docker.internal")
                return addr

            for i in pipeline.inputs:
                if i.input:
                    config["inputs"][i.input.input_id] = {
                        "topic": i.input.topic, 
                        "broker": fix_broker(i.input.broker_address)
                    }
            
            for o in pipeline.outputs:
                if o.output:
                    config["outputs"][o.output.output_id] = {
                        "topic": o.output.topic, 
                        "broker": fix_broker(o.output.broker_address)
                    }

            for t in pipeline.transformations:
                if t.transformation:
                    config["transformations"][t.transformation.transformation_id] = {
                        "script": t.transformation.python_script, 
                        "name": t.transformation.name
                    }

            for f in pipeline.flows:
                if f.flow:
                    config["flows"].append({
                        "start_type": f.flow.start_node_type.value,
                        "start_id": f.flow.start_node,
                        "end_type": f.flow.end_node_type.value,
                        "end_id": f.flow.end_node
                    })

            if not config["inputs"]:
                raise ValueError("Pipeline has no inputs.")

            # Spawn Worker Process
            process = multiprocessing.Process(target=run_pipeline_worker, args=(config,))
            process.start()

            cls._active_pipelines[pipeline_id] = {"process": process, "start_time": datetime.now()}
            return {"status": "started", "pipeline_id": pipeline_id}

        except Exception as e:
            logger.error(f"CRITICAL ERROR in start_pipeline: {str(e)}")
            traceback.print_exc()
            raise e

    @classmethod
    async def stop_pipeline(cls, pipeline_id: int):
        if pipeline_id in cls._active_pipelines:
            proc = cls._active_pipelines[pipeline_id]["process"]
            proc.terminate()
            proc.join(timeout=2)
            if proc.is_alive(): proc.kill()
            del cls._active_pipelines[pipeline_id]
        return {"status": "stopped", "pipeline_id": pipeline_id}


def run_pipeline_worker(config: Dict[str, Any]):
    try:
        print(f"[Worker] Starting worker for pipeline {config['pipeline_id']}")
        
        broker_instances = {}
        
        # --- Helpers defined inside to access config scope ---

        def get_end_node(start_id, start_type):
            for flow in config["flows"]:
                if flow["start_id"] == start_id and flow["start_type"] == start_type:
                    return {
                        "id": flow["end_id"],
                        "type": flow["end_type"]
                    }
            return None

        def get_callable_function_for_transformation(transform_id):
            t_data = config["transformations"][transform_id]
            local_scope = {}
            try:
                exec(t_data["script"], {}, local_scope)
                return local_scope.get("transform", lambda x: x)
            except Exception as e:
                print(f"Script Error: {e}")
                return lambda x: x

        def get_app(broker, broker_instances):
            if broker in broker_instances:
                return broker_instances[broker]
            else:
                print(f"[Worker] Initializing App for {broker}")
                app = Application(
                    broker_address=broker,
                    consumer_group=f"{config['group_id_prefix']}-{hash(broker)}",
                    auto_offset_reset="earliest",
                    consumer_extra_config={"enable.auto.commit": True}
                )
                broker_instances[broker] = app
                return app


        for input_id, input_data in config["inputs"].items():
            topic = input_data["topic"]
            broker = input_data["broker"]

            # Get App and Stream
            app = get_app(broker, broker_instances)
            topic_obj = app.topic(topic, value_deserializer="json")
            current_dataframe = app.dataframe(topic_obj)

            # Determine Next Node
            current_node = get_end_node(input_id, "input")
            
            if not current_node:
                print(f"Warning: Input {input_id} has no connections.")
                continue

            # Loop through Transformations
            while current_node["type"] == "transformation":
                
                # Apply Transform
                transform_func = get_callable_function_for_transformation(current_node["id"])
                current_dataframe = current_dataframe.apply(transform_func).filter(lambda x: x is not None)

                # Move to next node
                next_node = get_end_node(current_node["id"], "transformation")
                if not next_node:
                    # Dead end in graph
                    current_node = {"type": "dead_end"}
                    break
                
                current_node = next_node

            # 4. Handle Output
            if current_node["type"] == "output":
                output_data = config["outputs"][current_node["id"]]
                output_broker = output_data["broker"]
                output_topic_name = output_data["topic"]

                # Get app for output broker (might be same, might be different)
                app_out = get_app(output_broker, broker_instances)
                
                if output_broker == broker:
                    # Same broker -> Standard Binding
                    target_topic = app_out.topic(output_topic_name, value_serializer="json")
                    current_dataframe.to_topic(target_topic)
                else:
                    # Different broker -> Producer Sink
                    # We need a raw producer because we can't pipe dataframes across apps in memory
                    # Using a helper sink function to produce to app_out
                    print(f"[Worker] Bridging {broker} -> {output_broker}")
                    producer = app_out.get_producer()
                    
                    def send_foreign(value, key=None, timestamp=None, headers=None):
                        try:
                            producer.produce(
                                topic=output_topic_name,
                                value=json.dumps(value),
                                key=key
                            )
                        except Exception as e:
                            print(f"Sink Error: {e}")

                    current_dataframe.sink(send_foreign)

        print(f"Running {len(broker_instances)} Applications...")
        
        threads = []
        # Apply signal patch for threads
        original_sig = signal.signal
        signal.signal = lambda s, h: None 

        for broker, app in broker_instances.items():
            t = threading.Thread(target=app.run, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    except Exception as e:
        print(f"[Worker] Crashed: {e}")
        traceback.print_exc()