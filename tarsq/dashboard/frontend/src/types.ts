// ─── Domain types derived from tarsq/dashboard/api.py ────────────────────────
//
// All shapes here match the JSON the FastAPI backend actually returns.
// Field names are kept in snake_case to match the Python/Redis source — no
// translation layer that could silently diverge.

// ─── Status literals ──────────────────────────────────────────────────────────

/** Job lifecycle statuses as stored in Redis and returned by the API. */
export type JobStatus = 'queued' | 'in_progress' | 'completed' | 'failed'

// ─── Core domain objects ──────────────────────────────────────────────────────

/**
 * A single job record as returned by GET /api/jobs and GET /api/jobs/:id.
 *
 * Jobs are stored in Redis as hash maps via HSET; hgetall returns every value
 * as a string. The API layer currently returns the raw hash, so numeric fields
 * like `retries` arrive as strings over the wire. The `payload` field is a
 * JSON-encoded string that must be parsed before use.
 */
export interface Job {
  job_id: string
  task: string
  status: JobStatus
  /** Stored as a string in Redis (e.g. "2"). Parse with Number() before arithmetic. */
  retries: string
  created_at: string   // ISO 8601
  updated_at: string   // ISO 8601
  /** JSON-encoded string. Parse with JSON.parse before rendering. */
  payload: string
}

/**
 * A worker process entry as returned by GET /api/workers.
 *
 * Workers are synthesised from the tarsq:processing queue at request time;
 * they are not stored as persistent records.
 */
export interface Worker {
  /** Sequential integer assigned during the /api/workers response build. */
  worker_id: number
  status: 'active'
  /** The task name currently being processed, or null when idle. */
  current_job: string | null
  /** Uptime string (e.g. "2h 33m"), or null — not yet implemented in the API. */
  uptime: string | null
}

/**
 * A registered @schedule entry as returned by GET /api/schedules.
 *
 * Derived from cron_registry at request time; not persisted in Redis.
 */
export interface Schedule {
  name: string
  cron: string
  /** ISO 8601 datetime of the previous theoretical run, or null on error. */
  last_run: string | null
  /** ISO 8601 datetime of the next scheduled run, or null on error. */
  next_run: string | null
}

// ─── API response wrappers ────────────────────────────────────────────────────

/** GET /api/stats */
export interface StatsResponse {
  total: number
  queued: number
  in_progress: number
  completed: number
  failed: number
}

/** GET /api/jobs */
export interface JobsListResponse {
  jobs: Job[]
  total: number
}

/** GET /api/workers */
export interface WorkersResponse {
  queue_depth: number
  processing: number
  workers: Worker[]
}

/** GET /api/schedules */
export interface SchedulesResponse {
  schedules: Schedule[]
}
