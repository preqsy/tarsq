import asyncio
import signal
import importlib
import multiprocessing
from datetime import datetime, timezone
import inspect
import json
import pickle
import time

import redis

from tarsq.config import settings
from tarsq.core.decorator import registry
from tarsq.core.schemas import Job, Task, TaskStatusEnum
from tarsq.logger import log

processes: list[multiprocessing.Process] = []


class WorkerSettings:
    """Configuration for the tarsq worker process.

    Define a class with any subset of these attributes in your project.
    Inheritance from this class is optional — tarsq reads all settings
    via getattr() with fallbacks, so you only need to declare what you
    want to override.

    Pass the dotted path to your class via the CLI:
        tarsq --settings myapp.MyWorkerSettings

    Attributes:
        app: Dotted module path to import on startup so that @task and
            @schedule decorators register themselves (e.g. "myapp.tasks").
            If not set, only tasks already in scope will be available.
        workers: Number of concurrent worker processes. Defaults to 5.
        ctx: Shared context dict passed to every task handler. Avoid
            putting live resources (db sessions, connections) here directly
            — use on_startup to build them inside each worker process
            instead, since ctx is not pickled across process boundaries.
        on_startup: Optional sync or async function called inside each
            worker process after it spawns. Use this to initialise
            per-process resources (db connections, clients) and store them
            in the ctx dict.
        on_shutdown: Optional sync or async function called once in the
            main process after all workers have exited. Use this to flush
            or close any top-level resources.

    Example:
        import asyncio
        from tarsq import WorkerSettings

        async def startup(ctx):
            ctx["db"] = await create_db_pool()

        async def shutdown(ctx):
            await ctx["db"].close()

        class MyWorkerSettings(WorkerSettings):
            app = "myapp.tasks"
            workers = 4
            on_startup = startup
            on_shutdown = shutdown
    """

    app: str = None
    workers: int = 5
    ctx: dict = {}
    on_startup = None
    on_shutdown = None


def _check_ctx_picklable(worker_id: int, ctx: dict):
    for key, value in ctx.items():
        try:
            pickle.dumps(value)
        except Exception:
            log(
                worker_id,
                "WARN",
                f"ctx['{key}'] ({type(value).__name__}) is not picklable — tasks will fail with PicklingError. "
                f"Store a factory or class instead of a live instance.",
            )


def _run_task(ctx, func, payload):
    if inspect.iscoroutinefunction(func):
        asyncio.run(func(ctx, payload))
    else:
        func(ctx, payload)


def get_task_from_registry(task_name: str) -> Task:
    if task_name not in registry:
        raise ValueError(
            f"unknown task '{task_name}' — is the module containing @task('{task_name}') imported?"
        )
    return registry[task_name]


def handle_retry(
    job: Job,
    retries: int,
    worker_id: int,
    value: str,
    job_id: str,
    max_retries: int,
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
        f"{task_name} [{job_id[:8]}] — retrying in {delay}s (attempt {retries}/{max_retries})",
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


def worker(worker_id: int, app, shutdown_event, on_startup=None):
    if app:
        importlib.import_module(app)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    ctx = {}
    if on_startup:
        (
            asyncio.run(on_startup(ctx))
            if inspect.iscoroutinefunction(on_startup)
            else on_startup(ctx)
        )

    _check_ctx_picklable(worker_id, ctx)

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
                try:
                    p.join(timeout=timeout)

                    if p.is_alive():
                        p.kill()
                        p.join()
                        raise TimeoutError(f"task exceeded timeout of {timeout}s")

                    if p.exitcode != 0:
                        raise RuntimeError(
                            f"task process exited with code {p.exitcode}"
                        )
                finally:
                    p.close()

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
                        args=(
                            job_obj,
                            retries,
                            worker_id,
                            redis_value,
                            job_id,
                            max_retries,
                        ),
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


def watch(app, shutdown_event, on_startup=None):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if app:
        importlib.import_module(app)

    while not shutdown_event.is_set():
        for i, p in enumerate(processes):
            if not p.is_alive() and not shutdown_event.is_set():
                log(i, "WARN", "worker crashed — restarting")
                new_process = multiprocessing.Process(
                    target=worker,
                    args=(i, app, shutdown_event, on_startup),
                )
                processes[i] = new_process
                new_process.start()
        time.sleep(2)
