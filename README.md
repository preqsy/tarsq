# tarsq

A fast, production-ready task queue for Python backed by Redis.

## Features

- Simple `@task` decorator to register handlers (sync and async)
- `dispatch()` to enqueue jobs from anywhere in your app
- `status()` to track job progress
- Automatic retries (up to 3) with exponential backoff
- Configurable worker count and task timeout
- Startup/shutdown lifecycle hooks
- Crashed worker auto-restart
- Stuck task recovery on startup

## Requirements

- Python 3.11+
- Redis

## Installation

```bash
pip install tarsq
```

## Quick start

**1. Define your tasks** (`myapp/tasks.py`):

```python
from tarsq import task

@task("send_email")
def send_email(ctx, payload):
    print(f"Sending email to {payload['to']}")

@task("resize_image")
async def resize_image(ctx, payload):
    print(f"Resizing image at {payload['url']}")
```

**2. Configure the worker** (`myapp/worker_settings.py`):

```python
from tarsq import WorkerSettings

class MyWorkerSettings(WorkerSettings):
    app = "myapp.tasks"
    workers = 5
    timeout = 60
```

**3. Start the worker**:

```bash
tarsq --settings myapp.worker_settings.MyWorkerSettings
```

Or without a settings class:

```bash
tarsq --app myapp.tasks --workers 5 --timeout 60
```

**4. Dispatch jobs** from your application:

```python
from tarsq import dispatch, status

job_id = dispatch("send_email", payload={"to": "user@example.com"})

job = status(job_id)
print(job.status)  # queued | in_progress | completed | failed
```

## Configuration

### WorkerSettings

| Attribute    | Type       | Default | Description                                      |
|--------------|------------|---------|--------------------------------------------------|
| `app`        | `str`      | `None`  | Dotted module path containing your `@task` handlers |
| `workers`    | `int`      | `5`     | Number of concurrent worker threads              |
| `timeout`    | `int`      | `300`   | Max seconds a task can run before being killed   |
| `ctx`        | `dict`     | `{}`    | Shared context passed to every task handler      |
| `on_startup` | `callable` | `None`  | Called once before workers start (sync or async) |
| `on_shutdown`| `callable` | `None`  | Called once after workers stop (sync or async)   |

### Environment variables

| Variable         | Default     | Description         |
|------------------|-------------|---------------------|
| `REDIS_HOST`     | `localhost` | Redis host          |
| `REDIS_PORT`     | `6379`      | Redis port          |
| `REDIS_PASSWORD` | `None`      | Redis password      |

Variables can also be set in a `.env` file in your project root.

## Lifecycle hooks

```python
from tarsq import WorkerSettings

async def on_startup(ctx):
    ctx["db"] = await create_db_pool()

async def on_shutdown(ctx):
    await ctx["db"].close()

class MyWorkerSettings(WorkerSettings):
    app = "myapp.tasks"
    on_startup = on_startup
    on_shutdown = on_shutdown
```

The `ctx` dict is passed into every task handler, making it easy to share connections across tasks.

## Job status

```python
from tarsq import status, TaskStatusEnum

job = status(job_id)

job.job_id      # UUID string
job.task        # task name
job.status      # TaskStatusEnum: queued | in_progress | completed | failed
job.retries     # number of retry attempts so far
job.created_at  # ISO 8601 timestamp
job.updated_at  # ISO 8601 timestamp of last status change
```

## License

MIT
