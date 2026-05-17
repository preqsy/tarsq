const BASE = '/api'

async function get(path, params = {}) {
  const q = new URLSearchParams(params).toString()
  const url = `${BASE}${path}${q ? `?${q}` : ''}`
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  stats: ()            => get('/stats'),
  jobs:  (params = {}) => get('/jobs', params),
  job:   (jobId)       => get(`/jobs/${jobId}`),
  workers:   ()        => get('/workers'),
  schedules: ()        => get('/schedules'),
}
