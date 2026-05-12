from typing import Dict

from tarsq.core.schemas import Task

registry: Dict[str, Task] = {}
cron_registry = {}


def task(
    name: str,
    *,
    timeout: int = 30,
    max_retries: int = 3,
):
    """Register a function as a tarsq task handler.

    Decorates a function and adds it to the task registry under the given
    name. Both sync and async functions are supported. The worker will look
    up this name when a job is submitted, so it must match exactly what is
    passed to submit().

    Args:
        name: A unique string identifier for this task. This is the name
            you pass to submit() to enqueue it (e.g. "send_email").

    Example:
        @task("send_email")
        def send_email(payload):
            to = payload["to"]
            ...

        @task("resize_image")
        async def resize_image(payload):
            url = payload["url"]
            ...
    """

    def decorator(func):
        registry[name] = {
            "func": func,
            "timeout": timeout,
            "max_retries": max_retries,
        }
        registry[name] = Task(func=func, timeout=timeout, max_retries=max_retries)
        return func

    return decorator


CRON_PRESETS = {
    "every minute": "* * * * *",
    "every 5 minutes": "*/5 * * * *",
    "every hour": "0 * * * *",
    "every day at midnight": "0 0 * * *",
    "every day at 9am": "0 9 * * *",
    "every monday": "0 0 * * 1",
}


def schedule(name: str, cron: str = "0 9 * * *"):
    def decorator(func):
        resolved_cron = CRON_PRESETS.get(cron, cron)
        cron_registry[name] = {"func": func, "cron": resolved_cron}

        return func

    return decorator
