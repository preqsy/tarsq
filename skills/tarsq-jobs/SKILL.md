---
name: tarsq-jobs
description: Correct conventions for writing, enqueuing, scheduling, and configuring Tarsq background jobs (the `tarsq` Python job runtime — `@task`, `@schedule`, `dispatch()`, `status()`, `WorkerSettings`). Use this skill whenever work touches a Tarsq task handler or job dispatch — adding or editing a `@task`/`@schedule` function, calling `dispatch()`/`status()`, setting a job timeout or retry count, wiring `WorkerSettings`/`on_startup`/`ctx`, or moving slow work "into the background" / "onto the queue" in a project that depends on tarsq. Tarsq is not Celery, RQ, or arq — its handler signature, retry semantics, and lack of a result backend differ, so consult this before writing any job code even if the task looks trivial.
---

# Tarsq jobs

Tarsq runs **every job in its own subprocess**. That single fact explains most of its
API: timeouts are hard kills, return values are discarded, and handler arguments must
survive pickling. Claims below cite the source so they can be re-checked:
paths are relative to the repo root (`tarsq/` is the package).

## Handler contract

A handler is a module-level function taking exactly two positional arguments:

```python
def my_task(ctx, payload):
    ...
```

The worker calls `func(ctx, payload)` positionally (`tarsq/worker.py:86`), so:

- `ctx` — per-worker-process dict, populated by `WorkerSettings.on_startup`. Empty `{}` unless `on_startup` fills it (`tarsq/worker.py:145`).
- `payload` — the dict passed to `dispatch()`. Always a dict; `{}` when dispatch got `None` (`tarsq/client.py:46-49`).

Do not write `def my_task(ctx, url=None, **kwargs)`. It raises no error — `url` silently
receives the **entire payload dict** — which is why such handlers look broken at runtime
rather than at import. (`mock_tasks.py` in this repo still uses that older shape; the
two-argument form is what the worker actually calls.)

Both sync and async handlers work; an async handler is run via `asyncio.run()` inside its
own subprocess, so it gets a fresh event loop per job (`tarsq/worker.py:87-90`).

## Defining a job

```python
# myapp/tasks.py
from tarsq import task


@task("send_welcome_email", timeout=10, max_retries=2)
def send_welcome_email(ctx, payload):
    user_id = payload["user_id"]
    db = ctx["db"]()            # ctx holds factories, not live connections
    try:
        user = db.get(User, user_id)
        mailer.send(user.email, template="welcome")
    finally:
        db.close()


@task("resize_image")           # timeout=30, max_retries=3 by default
async def resize_image(ctx, payload):
    await process(payload["url"])
```

A real in-repo example with the correct signature (`scale_tasks.py:19-24`):

```python
@task(name="flaky_task", timeout=10, max_retries=3)
def flaky_task(ctx, payload):
    """Fails at a configurable rate to measure retry amplification under load."""
    failure_rate = payload.get("failure_rate", 0.3) if payload else 0.3
    if random.random() < failure_rate:
        raise RuntimeError("simulated failure")
```

Rules that come from the decorator itself (`tarsq/core/decorator.py:10-56`):

| Option | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | required | The dispatch key. Must match `dispatch("...")` exactly. |
| `timeout` | `int` (seconds) | `30` | Must be `> 0`, else `ValueError` at import. |
| `max_retries` | `int` | `3` | Must be `>= 0`, else `ValueError` at import. |

There are no other options. Tarsq has no `queue=`, `priority=`, `rate_limit=`,
`acks_late=`, `bind=`, `countdown=`, or `eta=` — don't carry those over from Celery/RQ.

Names are a flat global namespace; registering the same name twice **silently overwrites**
the first handler (`tests/test_dispatch_validation.py:73-81`).

## Enqueuing

```python
from tarsq import dispatch

job_id = dispatch("send_welcome_email", payload={"user_id": 42})
job_id = dispatch("send_welcome_email", payload=WelcomePayload(user_id=42))  # pydantic ok
job_id = dispatch("cleanup")                                                 # payload -> {}
```

`dispatch()` accepts a dict, a pydantic `BaseModel`, or `None` — anything else raises
`ValueError("Invalid type")`, and an unreachable broker raises `ConnectionError`
(`tarsq/client.py:20-73`). It returns a UUID string immediately; it does not wait, and
there is no `.delay()` / `.apply_async()` style call.

**Keep payloads JSON-safe.** The job is `json.dumps`-ed, and a pydantic payload goes
through plain `model_dump()`, so a `datetime`/`UUID`/`Decimal` field raises
`TypeError: Object of type datetime is not JSON serializable` at dispatch time. Pass
`.isoformat()` strings and `str(uuid)` instead.

Because the payload arrives as an unvalidated dict, validate at the top of the handler if
it matters (e.g. `WelcomePayload(**payload)`).

## Status — and the absence of results

```python
from tarsq import status

job = status(job_id)   # JobStatus | None  (None if the id is unknown)
job.status             # "queued" | "in_progress" | "completed" | "failed"
job.retries            # retry attempts so far
job.created_at, job.updated_at
```

**Tarsq has no result backend.** The subprocess runner ignores whatever the handler
returns (`tarsq/worker.py:86-90`, verified: the return value is dropped), and the job hash
stores only `job_id, task, status, retries, created_at, updated_at`
(`tarsq/client.py:60-70`). So never write `result = status(job_id).result` or expect
`dispatch()` to give you a value back. If a caller needs output, the handler must persist
it itself (DB row, cache key, object store) and the caller reads from there.

Failure detail is also not captured: an exception inside the handler only reaches the
worker as a non-zero exit code, so the job record says "failed" and the traceback goes to
the worker's console output (`tarsq/worker.py:235-238`). Log or report errors **inside**
the handler if anyone needs the reason.

## Scheduled (recurring) jobs

`@schedule` accepts a 5-field cron expression or a natural-language phrase, validated at
import time — a bad value raises `InvalidSchedule` immediately (`tarsq/scheduling/__init__.py:9-33`).
Full phrase list: `docs/scheduling_phrases.md`.

Important: `@schedule` writes to `cron_registry`, which only the scheduler reads, while the
worker resolves handlers from the `@task` `registry` (`tarsq/core/decorator.py:6-7, 90` vs
`tarsq/worker.py:93-98`). A name that is only scheduled therefore fails on pickup with
`unknown task '<name>'`. Register both decorators under the same name:

```python
@schedule("daily_report", cron="every weekday at 9am")
@task("daily_report", timeout=300, max_retries=1)
def daily_report(ctx, payload):      # payload is always {} for scheduled runs
    build_report()
```

The scheduler dispatches with no payload (`tarsq/cron.py:43`), so scheduled handlers must
not require payload keys. Cron matching is evaluated once a minute against **local** time
(`tarsq/cron.py:38-41`), and the scheduler needs `WorkerSettings.app` set — it imports that
module unconditionally on start (`tarsq/cron.py:25`).

## Running the worker

```python
# myapp/worker_settings.py
from tarsq import WorkerSettings


def startup(ctx):
    ctx["db"] = SessionLocal        # a factory — see the ctx note below


class MyWorkerSettings(WorkerSettings):
    app = "myapp.tasks"             # module imported so @task/@schedule register
    workers = 4                     # concurrent worker processes (default 5)
    on_startup = startup            # runs inside each worker process
    on_shutdown = None              # runs once in the main process at exit
```

```bash
tarsq --settings myapp.worker_settings.MyWorkerSettings
tarsq --app myapp.tasks --workers 4                  # no settings class
tarsq --app myapp.tasks --dashboard --port 8080      # needs pip install tarsq[dashboard]
```

Subclassing `WorkerSettings` is optional — the CLI reads every attribute with `getattr`
fallbacks (`tarsq/cli.py:104-108`). CLI flags override the settings class.

**`ctx` is built by `on_startup`, not by a `ctx` class attribute.** Each worker starts with
`ctx = {}` and only `on_startup(ctx)` fills it (`tarsq/worker.py:145-151`); a `ctx = {...}`
declared on `WorkerSettings` is passed only to `on_shutdown` (`tarsq/cli.py:108, 176-182`).
And because `ctx` is pickled into each job's subprocess, store factories/classes — a live
session or connection either fails to pickle or breaks across the process boundary. Tarsq
warns about unpicklable values at worker startup (`tarsq/worker.py:73-83`).

## Timeouts and retries

- The timeout is enforced by `p.join(timeout)` then `p.kill()` — **SIGKILL, no cleanup**. `finally` blocks, context managers, and `except` handlers inside the handler do not run (`tarsq/worker.py:228-233`). Anything that must be released on timeout needs an external guard (a lease/lock with its own TTL), not a `try/finally`.
- Set `timeout` above the realistic p99 of the work; a job killed at the deadline counts as a failure and consumes a retry.
- `max_retries=N` means N retries **after** the first attempt — N+1 total attempts (`tarsq/worker.py:253-286`).
- Backoff is fixed at `2 ** retries` seconds (2s, 4s, 8s, …) and is not configurable (`tarsq/worker.py:116`). The sleep happens in a side process, so the worker keeps consuming the queue.
- Timeouts, uncaught exceptions, and any non-zero process exit are all "failure" and all retried. Retrying sets the job back to `queued`; only exhaustion sets `failed`.
- `max_retries=0` for work that must never run twice (and see idempotency below).

## Delivery semantics

Jobs in flight sit in `tarsq:processing`, and on startup the CLI re-queues everything left
there from a previous run (`tarsq/cli.py:38-55`). Combined with retries, delivery is
**at-least-once**: write handlers to be idempotent (guard on a DB unique key, an
idempotency token, or a "already done" check) rather than assuming exactly-once.

There is one FIFO queue (`tarsq:queue`) shared by all tasks — no priorities, no per-task
queues, no routing. A flood of slow jobs delays everything behind them; the only knobs are
`workers` and `timeout`.

## Common mistakes

| Mistake | What actually happens |
|---|---|
| `def handler(ctx, user_id=None, **kwargs)` | No error; `user_id` gets the whole payload dict. Use `(ctx, payload)`. |
| Expecting a return value / `.result` | Return values are discarded; there is no result backend. Persist output yourself. |
| `@schedule` without a matching `@task` | Job dispatches, then fails with `unknown task '<name>'`. |
| Forgetting `app` (or `--app`) | Nothing is registered: `no tasks registered` warning, every job fails as unknown; the scheduler process also dies on `import_module(None)`. |
| `datetime`/`UUID`/`Decimal` in the payload | `TypeError` at `dispatch()`. Serialize to strings first. |
| Defining a task inside a function/closure, or as a lambda | Unpicklable under `spawn`; the job cannot be launched. Keep handlers at module level. |
| Live DB session or client in `ctx` | Pickling warning at startup, failures at job launch. Store factories; build per job. |
| `try/finally` cleanup relied on at timeout | SIGKILL skips it. Use external TTL-based cleanup. |
| Reusing a task name | Silently overwrites the earlier handler. |
| Celery/RQ options (`queue=`, `countdown=`, `priority=`, `acks_late=`) | `TypeError` — `@task` takes only `name`, `timeout`, `max_retries`. |
| Assuming job records expire | Nothing sets a TTL on `tarsq:job:*`; records accumulate in Redis until deleted. |

## Non-obvious runtime behavior

- Default multiprocessing start method on macOS/Windows is **spawn**, so each job re-imports the handler's module in a fresh interpreter. Module-level side effects (connecting, loading a model) run *per job* — put that work in `on_startup` + `ctx` instead, and keep import-time code cheap.
- Per-job subprocess spawn costs real wall time; very short tasks are dominated by that overhead (this repo measures it: `scale-test/subprocess_cost.py`, `scale_tasks.py:7-10`).
- `workers` is the concurrency limit: each worker process handles one job at a time while its child runs.
- A crashed worker is restarted automatically by the watcher (`tarsq/worker.py:301-316`); the in-flight job is recovered via `tarsq:processing` at next startup, not instantly.
- Redis config comes from `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD`, read from the environment or a `.env` file (`tarsq/config.py`). There is no broker URL argument.
- `tarsq.worker.cancel_job(job_id)` exists but reliably cancels only jobs still `queued` (it marks them `failed`); an `in_progress` job is not cancellable in a useful way, and it is not exported from `tarsq/__init__.py`.

## Adding a job to a project — checklist

1. Write the handler in the module named by `WorkerSettings.app` (or imported by it), signature `(ctx, payload)`, at module level.
2. Pick `timeout` from the realistic worst case and `max_retries` from whether the work is safely repeatable.
3. Make it idempotent; validate `payload` at the top.
4. Persist anything the caller needs — don't return it.
5. `dispatch("name", payload={...})` with JSON-safe values; keep the returned `job_id` if the caller will poll `status()`.
6. If recurring, stack `@schedule` over `@task` with the same name and require no payload keys.

A copy-paste starting point lives in `assets/task_template.py`.
