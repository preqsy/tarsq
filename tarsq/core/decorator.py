registry = {}


def task(name: str):
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
        registry[name] = func
        return func
    return decorator
