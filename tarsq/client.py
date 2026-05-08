import json
import uuid
from datetime import datetime, timezone
from typing import Union

import redis
from pydantic import BaseModel

from tarsq.config import settings
from tarsq.core.schemas import TaskStatusEnum, JobStatus

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    password=settings.REDIS_PASSWORD,
)


def dispatch(
    task_name: str,
    payload: Union[BaseModel, dict, None] = None,
) -> str:
    """Dispatch a task to the queue for processing.

    Pushes a job onto the Redis queue and creates a job record to track
    its status. The job will be picked up by the next available worker.

    Args:
        task_name: The name of the registered task to run. Must match the
            name used in the @task decorator (e.g. "send_email").
        payload: The data to pass to the task handler. Accepts a Pydantic
            BaseModel instance, a plain dict, or None. Defaults to {}.

    Returns:
        A unique job ID (UUID string) that can be used to check the status
        of the job via status().

    Raises:
        ConnectionError: If tarsq cannot reach the broker.

    Example:
        job_id = dispatch("send_email", payload={"to": "user@example.com"})
        job_id = dispatch("send_email", payload=EmailPayload(to="user@example.com"))
    """
    if isinstance(payload, BaseModel):
        payload = payload.model_dump()
    elif payload is None:
        payload = {}

    job_id = str(uuid.uuid4())
    job = {"job_id": job_id, "task": task_name, "payload": payload, "retries": 0}

    try:
        r.lpush("tarsq:queue", json.dumps(job))
        r.hset(
            f"tarsq:job:{job_id}",
            mapping={
                "job_id": job_id,
                "task": task_name,
                "status": TaskStatusEnum.QUEUED,
                "retries": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": "",
            },
        )
    except redis.RedisError as e:
        raise ConnectionError(f"Failed to connect to the broker: {e}") from e
    return job_id


def status(job_id: str) -> JobStatus | None:
    """Retrieve the current status of a dispatched job.

    Looks up the job record in Redis and returns its current state,
    including status, retry count, and timestamps.

    Args:
        job_id: The job ID returned by dispatch().

    Returns:
        A JobStatus object with the following fields:
            - job_id: The unique job identifier.
            - task: The name of the task that was dispatched.
            - status: One of "queued", "in_progress", "completed", "failed".
            - retries: Number of times the job has been retried.
            - created_at: ISO 8601 timestamp of when the job was dispatched.
            - updated_at: ISO 8601 timestamp of the last status change.
        Returns None if no job with the given ID exists.

    Raises:
        ConnectionError: If tarsq cannot reach the broker.

    Example:
        job = status(job_id)
        if job.status == "completed":
            print("done!")
    """
    try:
        data = r.hgetall(f"tarsq:job:{job_id}")
    except redis.RedisError as e:
        raise ConnectionError(f"Failed to connect to the broker: {e}") from e
    return JobStatus(**data) if data else None
