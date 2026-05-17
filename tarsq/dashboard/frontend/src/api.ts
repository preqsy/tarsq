import type {
  Job,
  Worker,
  Schedule,
  StatsResponse,
  JobsListResponse,
  WorkersResponse,
  SchedulesResponse,
} from './types'


const TASKS = [
  'send_email',
  'process_image',
  'generate_report',
  'sync_data',
  'send_notification',
] as const

const STATUSES = [
  'queued',
  'in_progress',
  'completed',
  'completed',
  'completed',
  'failed',
] as const

const MOCK_JOBS: Job[] = Array.from({ length: 60 }, (_, i) => {
  // Modulo guarantees these indices are in-bounds; non-null assertions are safe.
  const status = STATUSES[i % STATUSES.length]!
  const task   = TASKS[i % TASKS.length]!
  const created = new Date(Date.now() - (i * 97_000 + (i * 13) % 50_000)).toISOString()
  return {
    job_id:     `job_${(i + 1).toString().padStart(3, '0')}_${Math.random().toString(36).slice(2, 8)}`,
    task,
    status,
    retries:    (i % 3).toString(),
    created_at: created,
    updated_at: new Date(new Date(created).getTime() + 8_000 + i * 400).toISOString(),
    payload:    JSON.stringify({ user_id: 100 + i, email: `user${i}@example.com` }),
  }
})

const MOCK_WORKERS: Worker[] = Array.from({ length: 5 }, (_, i) => ({
  worker_id:   i + 1,
  status:      'active' as const,
  current_job: i % 2 === 0 ? TASKS[i % TASKS.length]! : null,
  uptime:      `${2 + i}h ${30 + i * 3}m`,
}))

const MOCK_SCHEDULES: Schedule[] = [
  {
    name:     'daily_report',
    cron:     '0 9 * * *',
    last_run: new Date(Date.now() - 3_600_000).toISOString(),
    next_run: new Date(Date.now() + 72_000_000).toISOString(),
  },
  {
    name:     'cleanup_old_jobs',
    cron:     '0 0 * * 0',
    last_run: new Date(Date.now() - 86_400_000).toISOString(),
    next_run: new Date(Date.now() + 518_400_000).toISOString(),
  },
  {
    name:     'sync_users',
    cron:     '*/15 * * * *',
    last_run: new Date(Date.now() - 600_000).toISOString(),
    next_run: new Date(Date.now() + 300_000).toISOString(),
  },
]

function mockStats(): StatsResponse {
  const counts = MOCK_JOBS.reduce<Record<string, number>>((acc, j) => {
    acc[j.status] = (acc[j.status] ?? 0) + 1
    return acc
  }, {})
  return {
    total:       MOCK_JOBS.length,
    queued:      counts['queued']      ?? 0,
    in_progress: counts['in_progress'] ?? 0,
    completed:   counts['completed']   ?? 0,
    failed:      counts['failed']      ?? 0,
  }
}

// ─── API (mock) ───────────────────────────────────────────────────────────────

function delay(ms = 120): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const api = {
  async stats(): Promise<StatsResponse> {
    await delay()
    return mockStats()
  },

  async jobs({ limit = 500 }: { limit?: number } = {}): Promise<JobsListResponse> {
    await delay()
    return { jobs: MOCK_JOBS.slice(0, limit), total: MOCK_JOBS.length }
  },

  async job(jobId: string): Promise<Job | null> {
    await delay()
    return MOCK_JOBS.find((j) => j.job_id === jobId) ?? null
  },

  async workers(): Promise<WorkersResponse> {
    await delay()
    return { queue_depth: 0, processing: 0, workers: MOCK_WORKERS }
  },

  async schedules(): Promise<SchedulesResponse> {
    await delay()
    return { schedules: MOCK_SCHEDULES }
  },
}
