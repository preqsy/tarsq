import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'
import type { Job, JobStatus } from '../types'

const PAGE_SIZE = 20

type StatusFilter = 'all' | JobStatus

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Jobs() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)

  useEffect(() => {
    async function load(): Promise<void> {
      try {
        const data = await api.jobs()
        setJobs(
          [...data.jobs].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          ),
        )
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    void load()
    const id = setInterval(() => { void load() }, 10_000)
    return () => clearInterval(id)
  }, [])

  const filtered = useMemo(() => {
    return jobs.filter((j) => {
      const q = search.toLowerCase()
      const matchSearch = !q || j.job_id.includes(q) || j.task.toLowerCase().includes(q)
      const matchStatus = statusFilter === 'all' || j.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [jobs, search, statusFilter])

  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))

  function handleFilter(val: string): void {
    // Value originates from our own <option> elements; cast is safe.
    setStatusFilter(val as StatusFilter)
    setPage(1)
  }

  function handleSearch(val: string): void {
    setSearch(val)
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Jobs</h1>
        <p className="mt-0.5 text-sm text-zinc-500">
          {filtered.length.toLocaleString()} job{filtered.length !== 1 ? 's' : ''}
          {statusFilter !== 'all' ? ` · ${statusFilter.replace('_', ' ')}` : ''}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600" />
          <input
            type="text"
            placeholder="Search by task name or job ID…"
            value={search}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleSearch(e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => handleFilter(e.target.value)}
          className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        {loading ? (
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-11 rounded-lg bg-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : paginated.length === 0 ? (
          <p className="py-12 text-center text-sm text-zinc-600">
            {jobs.length === 0 ? 'No jobs yet' : 'No jobs match your filters'}
          </p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800">
                    {['Job ID', 'Task', 'Status', 'Retries', 'Created', 'Updated'].map((h) => (
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
                  {paginated.map((job) => (
                    <tr
                      key={job.job_id}
                      onClick={() => navigate(`/jobs/${job.job_id}`)}
                      className="cursor-pointer transition-colors hover:bg-zinc-800/40"
                    >
                      <td className="py-3 pr-4 font-mono text-xs text-zinc-500">
                        {job.job_id.slice(0, 14)}…
                      </td>
                      <td className="py-3 pr-4 font-medium text-zinc-200">{job.task}</td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={job.status} />
                      </td>
                      <td className="py-3 pr-4 text-zinc-400">{job.retries}</td>
                      <td className="py-3 pr-4 text-xs text-zinc-500">{fmt(job.created_at)}</td>
                      <td className="py-3 text-xs text-zinc-500">{fmt(job.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between border-t border-zinc-800 pt-4">
                <p className="text-xs text-zinc-500">
                  Page {page} of {totalPages} · {filtered.length} results
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-30"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-30"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
