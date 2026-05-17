// ─── Mock data ────────────────────────────────────────────────────────────────

const TASKS = [
  'send_email',
  'process_image',
  'generate_report',
  'sync_data',
  'send_notification',
]
const STATUSES = [
  'queued',
  'in_progress',
  'completed',
  'completed',
  'completed',
  'failed',
]

const MOCK_JOBS = Array.from({ length: 60 }, (_, i) => {
  const status = STATUSES[i % STATUSES.length]
  const created = new Date(Date.now() - (i * 97_000 + (i * 13) % 50_000)).toISOString()
  return {
    job_id: `job_${(i + 1).toString().padStart(3, '0')}_${Math.random().toString(36).slice(2, 8)}`,
    task: TASKS[i % TASKS.length],
    status,
    retries: i % 3,
    created_at: created,
    updated_at: new Date(new Date(created).getTime() + 8_000 + i * 400).toISOString(),
    payload: { user_id: 100 + i, email: `user${i}@example.com` },
  }
})

const MOCK_WORKERS = Array.from({ length: 5 }, (_, i) => ({
  worker_id: i + 1,
  status: 'active',
  current_job: i % 2 === 0 ? TASKS[i % TASKS.length] : null,
  uptime: `${2 + i}h ${30 + i * 3}m`,
}))

const MOCK_SCHEDULES = [
  {
    name: 'daily_report',
    cron: '0 9 * * *',
    last_run: new Date(Date.now() - 3_600_000).toISOString(),
    next_run: new Date(Date.now() + 72_000_000).toISOString(),
  },
  {
    name: 'cleanup_old_jobs',
    cron: '0 0 * * 0',
    last_run: new Date(Date.now() - 86_400_000).toISOString(),
    next_run: new Date(Date.now() + 518_400_000).toISOString(),
  },
  {
    name: 'sync_users',
    cron: '*/15 * * * *',
    last_run: new Date(Date.now() - 600_000).toISOString(),
    next_run: new Date(Date.now() + 300_000).toISOString(),
  },
]

function mockStats() {
  const counts = MOCK_JOBS.reduce((acc, j) => {
    acc[j.status] = (acc[j.status] || 0) + 1
    return acc
  }, {})
  return {
    total: MOCK_JOBS.length,
    queued: counts.queued || 0,
    in_progress: counts.in_progress || 0,
    completed: counts.completed || 0,
    failed: counts.failed || 0,
  }
}

// ─── API (mock) ───────────────────────────────────────────────────────────────

function delay(ms = 120) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export const api = {
  async stats() {
    await delay()
    return mockStats()
  },

  async jobs({ limit = 500 } = {}) {
    await delay()
    return { jobs: MOCK_JOBS.slice(0, limit), total: MOCK_JOBS.length }
  },

  async job(jobId) {
    await delay()
    return MOCK_JOBS.find((j) => j.job_id === jobId) ?? null
  },

  async workers() {
    await delay()
    return { workers: MOCK_WORKERS }
  },

  async schedules() {
    await delay()
    return { schedules: MOCK_SCHEDULES }
  },
}
