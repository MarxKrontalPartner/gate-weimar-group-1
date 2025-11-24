import multiprocessing
import logging
import traceback
import json
import psutil
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict, deque

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

    ## this is singleton pattern. we want to use one QuixPipelineManager per pipeline  
    # (we don't want multiple instance of QuixPipelineManager for the same pipeline!)
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

            # 1. Fetch Graph
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

            # 2. Prepare Configuration
            config = {
                "pipeline_id": pipeline.pipeline_id,
                "group_id_prefix": f"pipeline-{pipeline.pipeline_id}",
                "inputs": {},
                "outputs": {},
                "transformations": {},
                "flows": []
            }

            # Helper to fix localhost for Docker (if we are running locally we need this!) TODO: I will remove when deploying!
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

            # 3. Spawn Worker Process
            process = multiprocessing.Process(target=run_federated_worker, args=(config,))
            process.start()

            cls._active_pipelines[pipeline_id] = {"process": process, "start_time": datetime.now()}
            return {"status": "started", "pipeline_id": pipeline_id}

        except Exception as e:
            logger.error(f"CRITICAL ERROR in start_pipeline: {str(e)}")
            traceback.print_exc()
            raise e

    @classmethod
    async def stop_pipeline(cls, pipeline_id: int):
        """Stop pipeline and ensure ALL child processes are killed"""
        if pipeline_id in cls._active_pipelines:
            proc = cls._active_pipelines[pipeline_id]["process"]
            
            try:
                # Use psutil to kill the process and ALL its children
                parent = psutil.Process(proc.pid)
                children = parent.children(recursive=True)  # Get all descendants
                
                # Terminate parent
                proc.terminate()
                
                # Wait briefly for graceful shutdown
                proc.join(timeout=3)
                
                # If still alive, force kill everything
                if proc.is_alive():
                    proc.kill()
                    for child in children:
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass  # Already dead
                
                proc.join()  # Clean up zombie
                
            except psutil.NoSuchProcess:
                # Process already dead
                pass
            except Exception as e:
                logger.error(f"Error stopping pipeline {pipeline_id}: {e}")
            finally:
                del cls._active_pipelines[pipeline_id]
        
        return {"status": "stopped", "pipeline_id": pipeline_id}


# ---------------------------------------------------------
# HELPER: TOPOLOGICAL SORT
# ---------------------------------------------------------
def _sort_flows_topologically(flows: List[Dict]) -> List[Dict]:
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    
    all_nodes = set()

    for flow in flows:
        u = f"{flow['start_type']}_{flow['start_id']}"
        v = f"{flow['end_type']}_{flow['end_id']}"
        adj[u].append(flow)
        in_degree[v] += 1
        if u not in in_degree: 
            in_degree[u] = 0
        all_nodes.add(u)
        all_nodes.add(v)

    queue = deque([n for n in all_nodes if in_degree[n] == 0])
    sorted_flows = []

    while queue:
        u = queue.popleft()
        if u in adj:
            for flow in adj[u]:
                sorted_flows.append(flow)
                v = f"{flow['end_type']}_{flow['end_id']}"
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

    if len(sorted_flows) != len(flows):
        print("Warning: Cycle detected or disconnected graph components.")
        processed_ids = {f"{f['start_type']}_{f['start_id']}->{f['end_type']}_{f['end_id']}" for f in sorted_flows}
        for f in flows:
            fid = f"{f['start_type']}_{f['start_id']}->{f['end_type']}_{f['end_id']}"
            if fid not in processed_ids:
                sorted_flows.append(f)

    return sorted_flows


# ---------------------------------------------------------
# CLUSTER APP: Runs in its own process per broker
# ---------------------------------------------------------
def run_cluster_app(broker_addr: str, input_ids: List[int], config: Dict[str, Any]):
    """
    Runs a Quixstreams application for one broker cluster.
    """
    try:
        print(f"[Cluster {multiprocessing.current_process().pid}] Starting for broker: {broker_addr}")
        
        # A. Compile Transformations
        transforms = {}
        for t_id, t_data in config["transformations"].items():
            local_scope = {}
            try:
                exec(t_data["script"], {}, local_scope)
                transforms[t_id] = local_scope.get("transform", lambda x: x)
            except Exception as e:
                print(f"[Cluster] Script Error in Transform {t_id}: {e}")
                transforms[t_id] = lambda x: x
        
        # B. Initialize Quixstreams App
        app = Application(
            broker_address=broker_addr,
            consumer_group=f"{config['group_id_prefix']}-{hash(broker_addr)}",
            auto_offset_reset="earliest",
            consumer_extra_config={"enable.auto.commit": True}
        )

        # C. Foreign Producers for cross-broker outputs
        foreign_apps = {}
        
        def get_foreign_producer(target_broker):
            if target_broker not in foreign_apps:
                foreign_apps[target_broker] = Application(
                    broker_address=target_broker,
                    consumer_group=f"{config['group_id_prefix']}-producer-{hash(target_broker)}"
                )
            return foreign_apps[target_broker].get_producer()

        # D. Build Streaming Graph
        streams = {}

        # Initialize inputs
        for i_id in input_ids:
            topic_name = config["inputs"][i_id]["topic"]
            topic = app.topic(topic_name, value_deserializer="json")
            streams[f"input_{i_id}"] = app.dataframe(topic)

        # Sort and apply flows
        ordered_flows = _sort_flows_topologically(config["flows"])

        for flow in ordered_flows:
            src_key = f"{flow['start_type']}_{flow['start_id']}"
            
            if src_key not in streams:
                continue

            current_stream = streams[src_key]

            if flow['end_type'] == 'transformation':
                t_id = flow['end_id']
                func = transforms[t_id]
                out_stream = current_stream.apply(func).filter(lambda x: x is not None)
                streams[f"transformation_{t_id}"] = out_stream

            elif flow['end_type'] == 'output':
                o_id = flow['end_id']
                out_conf = config["outputs"][o_id]
                
                if out_conf["broker"] == broker_addr:
                    # Same broker
                    target_topic = app.topic(out_conf["topic"], value_serializer="json")
                    current_stream.to_topic(target_topic)
                else:
                    # Different broker
                    target_broker = out_conf["broker"]
                    target_topic_name = out_conf["topic"]
                    
                    def send_foreign(value, key=None, timestamp=None, headers=None):
                        try:
                            producer = get_foreign_producer(target_broker)
                            producer.produce(
                                topic=target_topic_name,
                                value=json.dumps(value),
                                key=key
                            )
                        except Exception as e:
                            print(f"[Cluster] Foreign Sink Error: {e}")

                    current_stream.sink(send_foreign)

        print(f"[Cluster {multiprocessing.current_process().pid}] Starting event loop")
        app.run()

    except KeyboardInterrupt:
        print(f"[Cluster {multiprocessing.current_process().pid}] Interrupted")
    except Exception as e:
        print(f"[Cluster] Error: {e}")
        traceback.print_exc()


# ---------------------------------------------------------
# WORKER PROCESS: Spawns and manages cluster processes
# ---------------------------------------------------------
def run_federated_worker(config: Dict[str, Any]):
    """
    Coordinator process that spawns one child per broker.
    Simple version - no signal handling needed, psutil does the cleanup.
    """
    try:
        print(f"[Worker {multiprocessing.current_process().pid}] Starting pipeline {config['pipeline_id']}")
        
        # Group inputs by broker
        broker_groups = defaultdict(list)
        for i_id, i_data in config["inputs"].items():
            broker = i_data["broker"]
            broker_groups[broker].append(i_id)

        print(f"[Worker] Spawning {len(broker_groups)} cluster processes")

        # Spawn one process per broker
        processes = []
        for broker, inp_ids in broker_groups.items():
            p = multiprocessing.Process(
                target=run_cluster_app,
                args=(broker, inp_ids, config)
            )
            p.start()
            processes.append(p)
            print(f"[Worker] Started cluster process {p.pid} for broker {broker}")

        # Wait for all to complete
        for p in processes:
            p.join()
        
        print("[Worker] All cluster processes completed")

    except Exception as e:
        print(f"[Worker] Crashed: {e}")
        traceback.print_exc()