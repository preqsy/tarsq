from enum import Enum
from typing import Callable
from pydantic import BaseModel, Field


class TaskStatusEnum(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    task: str
    status: TaskStatusEnum
    retries: int
    created_at: str
    updated_at: str | None = None


class Job(BaseModel):
    job_id: str | None = None
    task: str
    payload: dict
    retries: int


class Task(BaseModel):
    func: Callable
    timeout: int
    max_retries: int
