# app/pipelines/lifecycle.py
import docker
import time
import json
import os

from app.pipelines.models import PipelineInput, PipelineStatus
from app.pipelines.registry import get_pipeline
from shared.logger import get_logger
from shared.events import emit_event

logger = get_logger("Lifecycle")

def stop_and_remove_container(container, name: str = None):
    """
    Safely stop and remove a Docker container.

    :param container: docker.models.containers.Container or None
    :param name: optional friendly name (e.g. 'worker', 'producer')
    """
    if not container:
        logger.info(f"No container to clean up{f' ({name})' if name else ''}.")
        return

    label = name or ''

    try:
        logger.info(f"Stopping container {label} ({container.short_id})")
        container.stop()
    except Exception as e:
        logger.warning(f"Failed to stop container {label}: {e}")

    try:
        logger.info(f"Removing container {label} ({container.short_id})")
        container.remove()
    except Exception as e:
        logger.warning(f"Failed to remove container {label}: {e}")

def manage_pipeline_lifecycle(pipeline: PipelineInput, segment_index: int = 0):
    state = get_pipeline(pipeline.pipeline_id)
    if state and state["status"] == PipelineStatus.FAILED:
        logger.warning(
            f"Pipeline {pipeline.pipeline_id} already FAILED — skipping lifecycle"
        )
        return
    
    client = docker.from_env()
    
    worker_image_name = os.environ.get("WORKER_IMAGE_NAME", "pipeline-orchestrator-worker:0.1.0")
    producer_image_name = os.environ.get("PRODUCER_IMAGE_NAME", "pipeline-orchestrator-producer:0.1.0")
    network_name = os.environ.get("DOCKER_NETWORK_NAME", "pipeline-orchestrator_redpanda_network")
    broker_address = os.environ.get("BROKER_ADDRESS", "redpanda:9092")

    worker_env_vars = {
        "PIPELINE_ID": pipeline.pipeline_id,
        "SEGMENT_INDEX": str(segment_index),
        "BROKER_ADDRESS": broker_address, 
        "INPUT_TOPIC": pipeline.input_topic,
        "OUTPUT_TOPIC": pipeline.output_topic,
        "TRANSFORMATIONS": json.dumps(pipeline.transformations), # Serialize the list of scripts into a JSON string
        "FASTAPI_EVENT_ENDPOINT": os.getenv("FASTAPI_EVENT_ENDPOINT")
    }

    producer_container = None
    worker_container = None

    try:
        emit_event(
            pipeline_id=pipeline.pipeline_id,
            segment_index=segment_index,
            category="lifecycle",
            type="segment_started",
            data={
                "input": pipeline.input_topic,
                "output": pipeline.output_topic,
            },
        )

        logger.info(
            f"[{pipeline.pipeline_id}] Spawning containers "
            f"(input={pipeline.input_topic}, output={pipeline.output_topic})"
        )

        # ---------------- PRODUCER ----------------
        if pipeline.allow_producer:
            logger.info("Launching PRODUCER container…")

            producer_env_vars = {
                "BROKER_ADDRESS": broker_address,
                "INPUT_TOPIC": pipeline.input_topic,
                "N_CHANNELS": str(pipeline.n_channels),
                "FREQUENCY": str(pipeline.frequency),
            }

            producer_container = client.containers.run(
                image=producer_image_name,
                command=["python", "-m", "app.producer"],
                detach=True,
                network=network_name,
                environment=producer_env_vars,
                name=f"producer_{pipeline.pipeline_id}_{segment_index}",
                auto_remove=False
            )
            logger.info(f"Producer container {producer_container.short_id} started")
        
        # ---------------- WORKER ----------------
        worker_container = client.containers.run(
            image=worker_image_name,
            command=["python", "-m", "app.worker"],
            detach=True,
            network=network_name,  
            environment=worker_env_vars,
            name=f"worker_{pipeline.pipeline_id}_{segment_index}",
            auto_remove=False 
        )

        logger.info(f"Worker container {worker_container.short_id} started — monitoring")

        # -----------------------
        # Container Monitoring
        # -----------------------
        container_runtime = pipeline.runtime
        poll_interval = min(10, max(1, container_runtime // 10)) # Keep polling interval between 1–10 seconds
        elapsed = 0

        while elapsed < container_runtime:

            # Check worker only if it exists
            if worker_container:
                worker_container.reload()
                worker_status = worker_container.status

                if worker_status == "exited":
                    logger.error("Worker exited unexpectedly — failing pipeline")
                    emit_event(
                        pipeline_id=pipeline.pipeline_id,
                        segment_index=segment_index,
                        category="lifecycle",
                        type="failed",
                        data="Worker container exited unexpectedly",
                    )

                    if producer_container:
                        stop_and_remove_container(producer_container, name="producer")

                    return

            # Check producer only if it exists
            if producer_container:
                producer_container.reload()
                producer_status = producer_container.status

                if producer_status == "exited":
                    logger.error("Producer exited unexpectedly — failing pipeline")
                    emit_event(
                        pipeline_id=pipeline.pipeline_id,
                        segment_index=segment_index,
                        category="lifecycle",
                        type="failed",
                        data="Producer container exited unexpectedly",
                    )

                    if worker_container:
                        stop_and_remove_container(worker_container, name="worker")

                    return

            logger.debug(f"Heartbeat — running {elapsed}s")                        
            time.sleep(poll_interval)
            elapsed += poll_interval

        if producer_container:
            stop_and_remove_container(producer_container, name="producer")

        time.sleep(5)

        if worker_container:
            stop_and_remove_container(worker_container, name="worker")

        emit_event(
            pipeline_id=pipeline.pipeline_id,
            segment_index=segment_index,
            category="lifecycle",
            type="segment_completed",
        )
        logger.info(f"[{pipeline.pipeline_id}] Segment - {segment_index} completed")

    except Exception as e:
        logger.exception(f"Lifecycle Manager failed: {e}")

        emit_event(
            pipeline_id=pipeline.pipeline_id,
            category="lifecycle",
            type="failed",
            data=str(e),
        )
        
        if worker_container:
            stop_and_remove_container(worker_container, name="worker")
            
        if producer_container:
            stop_and_remove_container(producer_container, name="producer")