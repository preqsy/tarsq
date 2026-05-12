from enum import Enum
from pydantic import BaseModel


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
