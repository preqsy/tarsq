"""Template for a tarsq task module.

Copy into the module referenced by WorkerSettings.app (e.g. myapp/tasks.py),
then delete whatever you don't need.

Reminders that the template encodes:
  - handlers are module-level functions taking exactly (ctx, payload)
  - the return value is discarded — persist results yourself
  - timeout is a hard SIGKILL, so no cleanup runs when it fires
  - delivery is at-least-once, so handlers must be idempotent
  - payload values must be JSON-serializable
"""

from pydantic import BaseModel

from tarsq import dispatch, schedule, status, task


# ── Optional: a payload model so dispatch sites and the handler agree ─────────
class WelcomePayload(BaseModel):
    user_id: int
    # Keep fields JSON-safe (str/int/float/bool/list/dict/None).
    # A datetime/UUID/Decimal field will fail at dispatch() — pass
    # value.isoformat() / str(value) instead.


# ── A one-off job ─────────────────────────────────────────────────────────────
@task("send_welcome_email", timeout=10, max_retries=2)
def send_welcome_email(ctx, payload):
    """Handler body: validate, do the work, persist, log."""
    data = WelcomePayload(**payload)        # payload arrives unvalidated

    db = ctx["db"]()                        # ctx holds factories, not live sessions
    try:
        user = db.get(User, data.user_id)   # noqa: F821 — replace with your model
        if user.welcome_sent_at:            # idempotency guard: at-least-once delivery
            return
        mailer.send(user.email, template="welcome")   # noqa: F821
        user.welcome_sent_at = now()                  # noqa: F821
        db.commit()
    except Exception:
        # The worker only sees a non-zero exit code, so log the detail here
        # if anyone needs to know *why* it failed.
        raise
    finally:
        # Runs on normal failure, but NOT when the timeout kills the process.
        db.close()


# ── An async job ──────────────────────────────────────────────────────────────
@task("resize_image", timeout=60)
async def resize_image(ctx, payload):
    """Async handlers get their own event loop inside the job subprocess."""
    await process(payload["url"])           # noqa: F821


# ── A recurring job ───────────────────────────────────────────────────────────
# @schedule alone is not enough: the worker resolves handlers from the @task
# registry, so both decorators must use the SAME name.
@schedule("daily_report", cron="every weekday at 9am")
@task("daily_report", timeout=300, max_retries=1)
def daily_report(ctx, payload):
    """Scheduled runs always arrive with payload == {} — require no keys."""
    build_report()                          # noqa: F821


# ── Dispatch side (from a web handler, CLI, another job, anywhere) ────────────
def enqueue_welcome(user_id: int) -> str:
    job_id = dispatch("send_welcome_email", payload=WelcomePayload(user_id=user_id))
    return job_id


def poll(job_id: str) -> str | None:
    job = status(job_id)                    # None if the id is unknown
    return job.status if job else None      # queued | in_progress | completed | failed
