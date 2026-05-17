from datetime import datetime, timezone

import redis
from croniter import croniter
from fastapi import APIRouter, HTTPException

from tarsq.config import settings
from tarsq.core.decorator import cron_registry

router = APIRouter()

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    password=settings.REDIS_PASSWORD,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _all_jobs() -> list[dict]:
    """Return all job hashes from Redis using a pipeline scan."""
    keys = list(r.scan_iter("tarsq:job:*", count=200))
    if not keys:
        return []
    pipe = r.pipeline()
    for key in keys:
        pipe.hgetall(key)
    return [row for row in pipe.execute() if row]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def stats():
    """Aggregate job counts by status."""
    jobs = _all_jobs()
    counts: dict[str, int] = {
        "total": len(jobs),
        "queued": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
    }
    for job in jobs:
        s = job.get("status", "")
        if s in counts:
            counts[s] += 1
    return counts


@router.get("/jobs")
async def list_jobs(status: str | None = None, limit: int = 500):
    """Return all jobs, optionally filtered by status."""
    jobs = _all_jobs()
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    # Sort newest first
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    jobs = jobs[:limit]
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Return a single job by ID."""
    data = r.hgetall(f"tarsq:job:{job_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return data


@router.get("/workers")
async def workers():
    """Return queue depth metrics (worker processes are not directly observable)."""
    try:
        queue_depth = r.llen("tarsq:queue")
        processing  = r.llen("tarsq:processing")
    except redis.RedisError:
        queue_depth = processing = 0

    # Build a worker list from the processing queue entries
    worker_rows = []
    try:
        raw = r.lrange("tarsq:processing", 0, -1)
        import json
        for i, item in enumerate(raw, start=1):
            try:
                job = json.loads(item)
                task_name = job.get("task", "unknown")
            except Exception:
                task_name = "unknown"
            worker_rows.append({
                "worker_id": i,
                "status": "active",
                "current_job": task_name,
                "uptime": None,
            })
    except redis.RedisError:
        pass

    return {
        "queue_depth": queue_depth,
        "processing": processing,
        "workers": worker_rows,
    }


@router.get("/schedules")
async def schedules():
    """Return registered @schedule entries with next-run times."""
    now = datetime.now(timezone.utc)
    rows = []
    for name, entry in cron_registry.items():
        cron_expr = entry["cron"]
        try:
            cron = croniter(cron_expr, now)
            next_run = cron.get_next(datetime).isoformat()
            prev_run = croniter(cron_expr, now).get_prev(datetime).isoformat()
        except Exception:
            next_run = prev_run = None
        rows.append({
            "name": name,
            "cron": cron_expr,
            "last_run": prev_run,
            "next_run": next_run,
        })
    return {"schedules": rows}
