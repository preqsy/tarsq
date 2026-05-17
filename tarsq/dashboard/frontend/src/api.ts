import type {
  Job,
  StatsResponse,
  JobsListResponse,
  WorkersResponse,
  SchedulesResponse,
} from './types'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  stats(): Promise<StatsResponse> {
    return get<StatsResponse>('/api/stats')
  },

  jobs({ limit = 500 }: { limit?: number } = {}): Promise<JobsListResponse> {
    return get<JobsListResponse>(`/api/jobs?limit=${limit}`)
  },

  job(jobId: string): Promise<Job | null> {
    return get<Job>(`/api/jobs/${jobId}`).catch(() => null)
  },

  workers(): Promise<WorkersResponse> {
    return get<WorkersResponse>('/api/workers')
  },

  schedules(): Promise<SchedulesResponse> {
    return get<SchedulesResponse>('/api/schedules')
  },
}
