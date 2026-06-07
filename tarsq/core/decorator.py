from typing import Dict

from tarsq.core.schemas import Task
from tarsq.scheduling import _normalize_schedule

registry: Dict[str, Task] = {}
cron_registry = {}


def task(
    name: str,
    *,
    timeout: int = 30,
    max_retries: int = 3,
):
    """Register a function as a tarsq task handler.

    Adds the decorated function to the task registry under the given name.
    Workers resolve tasks by this name at runtime, so it must match exactly
    what is passed to dispatch().

    Both sync and async functions are supported. Each task runs in its own
    subprocess, so timeouts are enforced with a hard process kill — not a
    cooperative signal.

    Args:
        name: Unique identifier for this task. Must match the name passed
            to dispatch() (e.g. "send_email").
        timeout: Maximum seconds the task subprocess is allowed to run
            before it is killed and marked as failed. Must be > 0.
            Defaults to 30.
        max_retries: How many times to retry on failure before giving up.
            Must be >= 0. Defaults to 3.

    Raises:
        ValueError: If timeout <= 0 or max_retries < 0.

    Example:
        @task("send_email", timeout=10, max_retries=2)
        def send_email(ctx, payload):
            send(payload["to"], payload["subject"])

        @task("resize_image")
        async def resize_image(ctx, payload):
            await process(payload["url"])
    """
    if timeout <= 0:
        raise ValueError(f"timeout must be greater than 0, got {timeout}")
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")

    def decorator(func):
        registry[name] = Task(func=func, timeout=timeout, max_retries=max_retries)
        return func

    return decorator


def schedule(name: str, cron: str = "0 9 * * *"):
    """Register a function as a recurring scheduled task.

    Adds the decorated function to the cron registry. The scheduler process
    evaluates registered crons every minute and dispatches a job whenever
    a cron expression matches the current time.

    Accepts either a standard 5-field cron expression or a natural-language
    phrase (see docs/scheduling_phrases.md for the full list).

    Args:
        name: Unique identifier for this scheduled task.
        cron: A 5-field cron expression (e.g. "0 9 * * *") or a
            natural-language phrase (e.g. "every weekday at 9:30am").
            Defaults to "0 9 * * *" (daily at 9am).

    Raises:
        InvalidSchedule: If the cron expression is not valid and doesn't
            match any recognised phrase.

    Example:
        @schedule("daily_report", cron="every day at 9am")
        def daily_report(ctx, payload):
            generate_report()

        @schedule("cleanup", cron="0 2 * * *")
        def cleanup(ctx, payload):
            purge_old_records()
    """
    def decorator(func):
        resolved_cron = _normalize_schedule(cron)
        cron_registry[name] = {"func": func, "cron": resolved_cron}
        return func

    return decorator
