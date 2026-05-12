import asyncio
import importlib
import multiprocessing
from datetime import datetime, timezone
import inspect
import json
import time

import redis

from tarsq.config import settings
from tarsq.core.decorator import registry
from tarsq.core.schemas import Job, Task, TaskStatusEnum
from tarsq.logger import log

shutdown_event = multiprocessing.Event()
processes: list[multiprocessing.Process] = []


class WorkerSettings:
    """Configuration class for the tarsq worker.

    Subclass this in your project to configure the worker instead of
    passing CLI arguments. Pass the path to your subclass via
    `tarsq --settings myapp.MyWorkerSettings`.

    Attributes:
        app: Dotted module path containing your @task handlers
            (e.g. "myapp.tasks"). The module will be imported on startup
            to register all tasks.
        workers: Number of concurrent worker threads to run. Defaults to 5.
        timeout: Maximum number of seconds a single task is allowed to run
            before it is killed and marked as failed. Defaults to 300.
        on_startup: Optional function (sync or async) called once before
            workers start. Use this to set up shared resources.
        on_shutdown: Optional function (sync or async) called once after
            all workers have stopped. Use this to clean up resources.

    Example:
        from tarsq import WorkerSettings

        async def startup():
            print("starting up...")

        async def shutdown():
            print("shutting down...")

        class MyWorkerSettings(WorkerSettings):
            app = "myapp.tasks"
            workers = 3
            timeout = 60
            on_startup = startup
            on_shutdown = shutdown
    """

    app: str = None
    workers: int = 5
    ctx: dict = {}
    on_startup = None
    on_shutdown = None


def _run_task(ctx, func, payload):
    if inspect.iscoroutinefunction(func):
        asyncio.run(func(ctx, payload))
    else:
        func(ctx, payload)


def get_task_from_registry(task_name: str) -> Task:
    if task_name not in registry:
        raise ValueError(f"Unknown task: {task_name}")
    return registry[task_name]


def handle_retry(
    job: Job,
    retries: int,
    worker_id: int,
    value: str,
    job_id: str,
):
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        password=settings.REDIS_PASSWORD,
    )

    delay = 2**retries
    task_name = job.task
    log(
        worker_id,
        "RETRY",
        f"{task_name} [{job_id[:8]}] — retrying in {delay}s (attempt {retries}/3)",
    )
    time.sleep(delay)

    updated_at = datetime.now(timezone.utc).isoformat()
    job.retries = retries

    r.hset(
        f"tarsq:job:{job_id}",
        mapping={
            "status": TaskStatusEnum.QUEUED,
            "retries": retries,
            "updated_at": updated_at,
        },
    )
    r.lrem("tarsq:processing", 1, value)
    r.lpush("tarsq:queue", json.dumps(job.model_dump()))


def worker(worker_id: int, app, ctx: dict):
    importlib.import_module(app)

    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        password=settings.REDIS_PASSWORD,
    )

    while not shutdown_event.is_set():
        redis_value = r.blmove(
            "tarsq:queue",
            "tarsq:processing",
            timeout=1,
            src="RIGHT",
            dest="LEFT",
        )

        if redis_value is None:
            continue

        job_dict = json.loads(redis_value)

        job_obj = Job(**job_dict)

        task_name = job_obj.task
        task_payload = job_obj.payload
        retries = job_obj.retries

        job_id = job_obj.job_id

        if not job_id:
            continue

        updated_at = datetime.now(timezone.utc).isoformat()
        r.hset(
            f"tarsq:job:{job_id}",
            mapping={
                "status": TaskStatusEnum.IN_PROGRESS,
                "updated_at": updated_at,
            },
        )

        try:
            task = get_task_from_registry(task_name)

            func = task.func
            timeout = task.timeout
            max_retries = task.max_retries

            log(worker_id, "INFO", f"picked up  {task_name} [{job_id[:8]}]")
            try:
                start = time.monotonic()
                p = multiprocessing.Process(
                    target=_run_task,
                    args=(ctx, func, task_payload),
                )
                p.start()
                p.join(timeout=timeout)

                if p.is_alive():
                    p.kill()
                    p.join()
                    raise TimeoutError(f"task exceeded timeout of {timeout}s")

                if p.exitcode != 0:
                    raise RuntimeError(f"task process exited with code {p.exitcode}")

                elapsed = time.monotonic() - start
                r.hset(
                    f"tarsq:job:{job_id}", mapping={"status": TaskStatusEnum.COMPLETED}
                )
                r.lrem("tarsq:processing", 1, redis_value)
                log(
                    worker_id,
                    "INFO",
                    f"completed  {task_name} [{job_id[:8]}] — {elapsed:.2f}s",
                )

            except Exception as e:
                retries += 1
                log(
                    worker_id,
                    "ERROR",
                    f"failed     {task_name} [{job_id[:8]}] — {type(e).__name__}: {e} (attempt {retries}/{task.max_retries})",
                )
                if retries <= max_retries:
                    multiprocessing.Process(
                        target=handle_retry,
                        args=(job_obj, retries, worker_id, redis_value, job_id),
                    ).start()
                else:
                    log(
                        worker_id,
                        "ERROR",
                        f"gave up    {task_name} [{job_id[:8]}] — max retries reached",
                    )
                    updated_at = datetime.now(timezone.utc).isoformat()
                    r.hset(
                        f"tarsq:job:{job_id}",
                        mapping={
                            "status": TaskStatusEnum.FAILED,
                            "updated_at": updated_at,
                        },
                    )
                    r.lrem("tarsq:processing", 1, redis_value)

        except ValueError as e:
            log(worker_id, "WARN", str(e))


def watch(app, ctx: dict = None):
    importlib.import_module(app)
    while not shutdown_event.is_set():
        for i, p in enumerate(processes):
            if not p.is_alive() and not shutdown_event.is_set():
                log(i, "WARN", "crashed — restarting")
                new_process = multiprocessing.Process(
                    target=worker,
                    args=(i, app),
                    kwargs={"ctx": ctx},
                )
                processes[i] = new_process
                new_process.start()
        time.sleep(2)
