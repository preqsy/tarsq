# tarsq

The background job runtime for Python. Tasks run in their own subprocess. Timeouts are hard kills. Crashed workers restart themselves.

## Features

- `@task` decorator to register handlers — sync and async
- `@schedule` decorator for cron-based recurring tasks
- `dispatch()` to enqueue jobs from anywhere in your app
- `status()` to track job progress
- Each task runs in its own subprocess — timeouts enforced with a hard process kill
- Automatic retries with exponential backoff
- Per-worker context via `on_startup`
- Crashed worker auto-restart
- Stuck job recovery on startup

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

@task("send_email", timeout=10, max_retries=2)
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
    workers = 4
```

**3. Start the worker**:

```bash
tarsq --settings myapp.worker_settings.MyWorkerSettings
```

Or without a settings class:

```bash
tarsq --app myapp.tasks --workers 4
```

**4. Dispatch jobs** from anywhere in your application:

```python
from tarsq import dispatch, status

job_id = dispatch("send_email", payload={"to": "user@example.com"})

job = status(job_id)
print(job.status)  # queued | in_progress | completed | failed
```

## The `@task` decorator

```python
@task("send_email", timeout=30, max_retries=3)
def send_email(ctx, payload):
    ...
```

| Parameter     | Type  | Default | Description                                             |
|---------------|-------|---------|---------------------------------------------------------|
| `name`        | `str` | —       | Unique task name. Must match what is passed to dispatch() |
| `timeout`     | `int` | `30`    | Max seconds before the task process is killed. Must be > 0 |
| `max_retries` | `int` | `3`     | Retry attempts on failure. Must be >= 0                 |

Both sync and async functions are supported. Each task receives:
- `ctx` — dict populated by `on_startup`, containing shared resources
- `payload` — the dict passed to `dispatch()`

## Scheduled tasks

Use `@schedule` to register tasks that run automatically on a cron schedule:

```python
from tarsq import schedule

@schedule("daily_report", cron="every day at 9am")
def daily_report(ctx, payload):
    generate_report()

@schedule("cleanup", cron="0 2 * * *")
def cleanup(ctx, payload):
    purge_old_records()
```

Built-in presets:

| Preset                    | Cron expression |
|---------------------------|-----------------|
| `"every minute"`          | `* * * * *`     |
| `"every 5 minutes"`       | `*/5 * * * *`   |
| `"every hour"`            | `0 * * * *`     |
| `"every day at midnight"` | `0 0 * * *`     |
| `"every day at 9am"`      | `0 9 * * *`     |
| `"every monday"`          | `0 0 * * 1`     |

Standard 5-field cron expressions are also accepted.

## WorkerSettings

| Attribute     | Type       | Default | Description                                                         |
|---------------|------------|---------|---------------------------------------------------------------------|
| `app`         | `str`      | `None`  | Dotted module path to import so `@task` decorators register         |
| `workers`     | `int`      | `5`     | Number of concurrent worker processes                               |
| `on_startup`  | `callable` | `None`  | Sync or async function called inside each worker process on spawn. Receives `ctx` as argument |
| `on_shutdown` | `callable` | `None`  | Sync or async function called once in the main process after all workers exit |

Inheritance from tarsq's `WorkerSettings` is optional — only define the attributes you need.

## Context & on_startup

`on_startup` runs inside each worker process after it spawns. Use it to initialise per-process resources and store them in `ctx`. Every task handler receives this `ctx`.

```python
from tarsq import WorkerSettings

def startup(ctx):
    ctx["db"] = SessionLocal  # store the factory, not a live session

class MyWorkerSettings(WorkerSettings):
    app = "myapp.tasks"
    on_startup = startup
```

```python
@task("create_user")
def create_user(ctx, payload):
    db = ctx["db"]()  # create a session inside the task
    ...
    db.close()
```

> **Note:** `ctx` is pickled when passed to the task subprocess. Do not store live resources (db sessions, open connections) directly in `ctx` — store factories or classes instead. tarsq will warn you at startup if it detects unpicklable values.

## Job status

```python
from tarsq import status

job = status(job_id)

job.job_id      # UUID string
job.task        # task name
job.status      # "queued" | "in_progress" | "completed" | "failed"
job.retries     # number of retry attempts so far
job.created_at  # ISO 8601 timestamp
job.updated_at  # ISO 8601 timestamp of last status change
```

Returns `None` if no job with the given ID exists.

## Environment variables

| Variable         | Default     | Description    |
|------------------|-------------|----------------|
| `REDIS_HOST`     | `localhost` | Redis host     |
| `REDIS_PORT`     | `6379`      | Redis port     |
| `REDIS_PASSWORD` | `None`      | Redis password |

Variables can be set in a `.env` file in your project root.

## CLI reference

```bash
tarsq [--settings <path>] [--app <module>] [--workers <n>]
```

| Option       | Description                                              |
|--------------|----------------------------------------------------------|
| `--settings` | Dotted path to a `WorkerSettings` class                  |
| `--app`      | Dotted module path containing `@task`/`@schedule` handlers |
| `--workers`  | Number of worker processes (overrides `WorkerSettings`)  |

CLI args take priority over `WorkerSettings`.

## License

MIT
