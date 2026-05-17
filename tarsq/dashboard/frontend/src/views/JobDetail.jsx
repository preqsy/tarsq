import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function Field({ label, children }) {
  return (
    <div className="flex items-start gap-4 py-3">
      <dt className="w-28 shrink-0 text-sm text-zinc-500">{label}</dt>
      <dd className="text-sm text-zinc-200">{children}</dd>
    </div>
  )
}

export default function JobDetail() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    api
      .job(jobId)
      .then((data) => {
        if (!data) setNotFound(true)
        else setJob(data)
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [jobId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-indigo-500" />
      </div>
    )
  }

  if (notFound || !job) {
    return (
      <div className="py-16 text-center">
        <p className="text-zinc-500">Job not found.</p>
        <button
          onClick={() => navigate('/jobs')}
          className="mt-3 text-sm text-indigo-400 hover:text-indigo-300"
        >
          ← Back to Jobs
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <button
          onClick={() => navigate('/jobs')}
          className="mt-0.5 text-zinc-500 transition-colors hover:text-zinc-300"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-zinc-100">Job Detail</h1>
            <StatusBadge status={job.status} />
          </div>
          <p className="mt-0.5 font-mono text-xs text-zinc-500">{job.job_id}</p>
        </div>
      </div>

      {/* Details */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h2 className="mb-2 text-sm font-medium text-zinc-400">Details</h2>
        <dl className="divide-y divide-zinc-800">
          <Field label="Job ID">
            <span className="font-mono text-xs">{job.job_id}</span>
          </Field>
          <Field label="Task">
            <span className="font-medium">{job.task}</span>
          </Field>
          <Field label="Status">
            <StatusBadge status={job.status} />
          </Field>
          <Field label="Retries">{job.retries}</Field>
          <Field label="Created">{fmt(job.created_at)}</Field>
          <Field label="Updated">{fmt(job.updated_at)}</Field>
        </dl>
      </div>

      {/* Payload */}
      {job.payload && Object.keys(job.payload).length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <h2 className="mb-3 text-sm font-medium text-zinc-400">Payload</h2>
          <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs text-zinc-300">
            {JSON.stringify(job.payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
