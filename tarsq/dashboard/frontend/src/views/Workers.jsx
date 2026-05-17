import { useState, useEffect } from 'react'
import { api } from '../api'
import StatCard from '../components/StatCard'

export default function Workers() {
  const [workers, setWorkers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const [w, s] = await Promise.all([api.workers(), api.stats()])
      setWorkers(w.workers ?? [])
      setStats(s)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Workers</h1>
        <p className="mt-0.5 text-sm text-zinc-500">Worker process status · refreshes every 5s</p>
      </div>

      {/* Queue metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard
          label="Queue Depth"
          value={(stats?.queued ?? '—').toString()}
          color="amber"
        />
        <StatCard
          label="Processing"
          value={(stats?.in_progress ?? '—').toString()}
          color="blue"
        />
        <StatCard
          label="Workers"
          value={workers.length.toString()}
        />
      </div>

      {/* Worker list */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h2 className="mb-4 text-sm font-medium text-zinc-400">Worker Processes</h2>

        {loading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-14 rounded-lg bg-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : workers.length === 0 ? (
          <p className="py-10 text-center text-sm text-zinc-600">No workers running</p>
        ) : (
          <div className="space-y-2">
            {workers.map((w) => (
              <div
                key={w.worker_id}
                className="flex items-center gap-4 rounded-lg border border-zinc-800 px-4 py-3"
              >
                <div
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    w.status === 'active' ? 'bg-emerald-400' : 'bg-zinc-600'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-200">Worker {w.worker_id}</p>
                  <p className="truncate text-xs text-zinc-500">
                    {w.current_job ? `Processing: ${w.current_job}` : 'Idle'}
                  </p>
                </div>
                {w.uptime && (
                  <span className="shrink-0 text-xs text-zinc-600">{w.uptime}</span>
                )}
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    w.status === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-zinc-500/10 text-zinc-500'
                  }`}
                >
                  {w.status ?? 'unknown'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
