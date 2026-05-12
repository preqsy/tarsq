import asyncio
import concurrent.futures
from datetime import datetime, timezone
import inspect
import json
import threading
import time

import redis

from tarsq.config import settings
from tarsq.core.decorator import registry
from tarsq.core.schemas import TaskStatusEnum
from tarsq.logger import log

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    password=settings.REDIS_PASSWORD,
)

shutdown_event = threading.Event()
threads: list[threading.Thread] = []


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


def get_task_from_registry(task_name: str) -> dict:
    if task_name not in registry:
        raise ValueError(f"Unknown task: {task_name}")
    return registry[task_name]


def handle_retry(
    item_dict: dict, retries: int, worker_id: int, value: str, job_id: str
):
    delay = 2**retries
    task_name = item_dict["task"]
    log(
        worker_id,
        "RETRY",
        f"{task_name} [{job_id[:8]}] — retrying in {delay}s (attempt {retries}/3)",
    )
    time.sleep(delay)

    updated_at = datetime.now(timezone.utc).isoformat()
    item_dict["retries"] = retries

    r.hset(
        f"tarsq:job:{job_id}",
        mapping={
            "status": TaskStatusEnum.QUEUED,
            "retries": retries,
            "updated_at": updated_at,
        },
    )
    r.lrem("tarsq:processing", 1, value)
    r.lpush("tarsq:queue", json.dumps(item_dict))


def worker(worker_id: int, ctx: dict):
    while not shutdown_event.is_set():
        value = r.blmove(
            "tarsq:queue",
            "tarsq:processing",
            timeout=1,
            src="RIGHT",
            dest="LEFT",
        )

        if value is None:
            continue

        item_dict = json.loads(value)
        task_name = item_dict["task"]
        task_payload = item_dict["payload"]
        retries = item_dict["retries"]
        job_id = item_dict.get("job_id", None)

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

            func = task["func"]
            timeout = task["timeout"]
            max_retries = task["max_retries"]

            log(worker_id, "INFO", f"picked up  {task_name} [{job_id[:8]}]")
            try:
                start = time.monotonic()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        _run_task,
                        ctx,
                        func,
                        task_payload,
                    )

                    future.result(timeout=timeout)

                elapsed = time.monotonic() - start
                r.hset(
                    f"tarsq:job:{job_id}", mapping={"status": TaskStatusEnum.COMPLETED}
                )
                r.lrem("tarsq:processing", 1, value)
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
                    f"failed     {task_name} [{job_id[:8]}] — {type(e).__name__}: {e} (attempt {retries}/3)",
                )
                if retries <= max_retries:
                    threading.Thread(
                        target=handle_retry,
                        args=(item_dict, retries, worker_id, value, job_id),
                        daemon=True,
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
                    r.lrem("tarsq:processing", 1, value)

        except ValueError as e:
            log(worker_id, "WARN", str(e))


def watch(ctx: dict = None):
    while not shutdown_event.is_set():
        for i, t in enumerate(threads):
            if not t.is_alive() and not shutdown_event.is_set():
                log(i, "WARN", "crashed — restarting")
                new_thread = threading.Thread(
                    target=worker,
                    args=(i,),
                    kwargs={"ctx": ctx},
                    daemon=True,
                )
                threads[i] = new_thread
                new_thread.start()
        time.sleep(2)
