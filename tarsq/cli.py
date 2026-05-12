import argparse
import multiprocessing
import importlib
import inspect
import signal
import threading
import time

import redis

from tarsq.config import settings
from tarsq.core.decorator import registry
from tarsq.cron import scheduler
from tarsq.logger import sys_log
from tarsq.worker import WorkerSettings, worker, watch, processes


def print_registry():
    if not registry:
        sys_log("WARN", "no tasks registered — did you pass --app or --settings?")
        return

    max_len = max(len(name) for name in registry)
    width = max_len + 20

    print(f"\n  {'REGISTERED TASKS':^{width}}")
    print(f"  {'─' * width}")
    for name, func in registry.items():
        kind = "async" if inspect.iscoroutinefunction(func.func) else "sync"
        print(f"  ✓  {name:<{max_len}}   [{kind}]")
    print(f"  {'─' * width}")
    print(f"  {len(registry)} task(s) registered\n")


def recover_stuck_tasks():
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        password=settings.REDIS_PASSWORD,
    )

    stuck = r.lrange("tarsq:processing", 0, -1)
    if stuck:
        sys_log("WARN", f"recovering {len(stuck)} stuck task(s) from previous run")
        for item in stuck:
            r.lpush("tarsq:queue", item)
        r.delete("tarsq:processing")
        sys_log("INFO", "recovery complete")


def _load_settings(settings_path: str) -> WorkerSettings:
    module_path, class_name = settings_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def start():
    _manager = multiprocessing.Manager()
    shutdown_event = _manager.Event()

    parser = argparse.ArgumentParser(description="Start tarsq workers")
    parser.add_argument(
        "--settings",
        type=str,
        help="Path to WorkerSettings class (e.g. 'myapp.WorkerSettings')",
    )
    parser.add_argument(
        "--app", type=str, help="Module containing task handlers (e.g. 'myapp.tasks')"
    )
    parser.add_argument("--workers", type=int, help="Number of workers (default: 5)")

    args = parser.parse_args()

    ws = WorkerSettings()

    if args.settings:
        ws = _load_settings(args.settings)

    if args.app:
        ws.app = args.app
    if args.workers:
        ws.workers = args.workers

    app = getattr(ws, "app", None)
    workers = getattr(ws, "workers", 5)
    on_startup = getattr(ws, "on_startup", None)
    on_shutdown = getattr(ws, "on_shutdown", None)
    ctx = getattr(ws, "ctx", {})

    if app:
        importlib.import_module(app)
    else:
        sys_log("WARN", "no --app specified and WorkerSettings.app is not set — tasks registered in external modules won't be available")

    def handle_signal(sig, frame):
        sys_log("WARN", "shutdown signal received — waiting for workers to finish")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    recover_stuck_tasks()
    print_registry()
    sys_log("INFO", f"starting {workers} workers")

    for i in range(workers):
        p = multiprocessing.Process(
            target=worker,
            args=(i, app, shutdown_event, on_startup),
        )
        processes.append(p)

    print()
    for i, p in enumerate(processes):
        from tarsq.logger import log

        log(i, "INFO", "started")
        p.start()

    print()
    p_worker = multiprocessing.Process(
        target=watch,
        args=(app, shutdown_event, on_startup),
    )

    multiprocessing.Process(
        target=scheduler,
        args=(shutdown_event,),
        daemon=True,
    ).start()
    p_worker.start()

    while not shutdown_event.is_set():
        time.sleep(1)

    for p in processes:
        p.join()

    if on_shutdown:
        if inspect.iscoroutinefunction(on_shutdown):
            import asyncio

            asyncio.run(on_shutdown(ctx))
        else:
            on_shutdown(ctx)
    p_worker.join()
    sys_log("INFO", "all workers stopped — goodbye")
