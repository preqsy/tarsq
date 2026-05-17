import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { api } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Overview() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [recentJobs, setRecentJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    try {
      const [s, j] = await Promise.all([api.stats(), api.jobs({ limit: 8 })])
      setStats(s)
      setRecentJobs(
        [...(j.jobs ?? [])].sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at),
        ).slice(0, 8),
      )
    } catch {
      // silently ignore — backend may not be running yet
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 10_000)
    return () => clearInterval(id)
  }, [])

  async function handleRefresh() {
    setRefreshing(true)
    await load()
    setRefreshing(false)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Overview</h1>
          <p className="mt-0.5 text-sm text-zinc-500">Real-time job queue metrics</p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 rounded-xl border border-zinc-800 bg-zinc-900 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard label="Total Jobs" value={(stats?.total ?? 0).toLocaleString()} />
          <StatCard label="Queued" value={(stats?.queued ?? 0).toLocaleString()} color="amber" />
          <StatCard label="In Progress" value={(stats?.in_progress ?? 0).toLocaleString()} color="blue" />
          <StatCard label="Completed" value={(stats?.completed ?? 0).toLocaleString()} color="emerald" />
          <StatCard label="Failed" value={(stats?.failed ?? 0).toLocaleString()} color="red" />
        </div>
      )}

      {/* Recent jobs */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-medium text-zinc-300">Recent Jobs</h2>
          <button
            onClick={() => navigate('/jobs')}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            View all →
          </button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 rounded-lg bg-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <p className="py-10 text-center text-sm text-zinc-600">No jobs yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  {['Job ID', 'Task', 'Status', 'Retries', 'Created'].map((h) => (
                    <th
                      key={h}
                      className="pb-3 pr-4 text-left text-xs font-medium uppercase tracking-wider text-zinc-500 last:pr-0"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {recentJobs.map((job) => (
                  <tr
                    key={job.job_id}
                    onClick={() => navigate(`/jobs/${job.job_id}`)}
                    className="cursor-pointer transition-colors hover:bg-zinc-800/40"
                  >
                    <td className="py-3 pr-4 font-mono text-xs text-zinc-500">
                      {job.job_id.slice(0, 16)}…
                    </td>
                    <td className="py-3 pr-4 font-medium text-zinc-200">{job.task}</td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-3 pr-4 text-zinc-400">{job.retries}</td>
                    <td className="py-3 text-xs text-zinc-500">{fmt(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
