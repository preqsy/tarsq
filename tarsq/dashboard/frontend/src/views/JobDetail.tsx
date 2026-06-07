import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'
import type { Job } from '../types'

function fmt(iso: string | null): string {
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

interface FieldProps {
  label: string
  children: React.ReactNode
}

function Field({ label, children }: FieldProps) {
  return (
    <div className="flex items-start gap-4 py-3">
      <dt className="w-28 shrink-0 text-sm text-zinc-500">{label}</dt>
      <dd className="text-sm text-zinc-200">{children}</dd>
    </div>
  )
}

/**
 * Parses the job's payload JSON string and returns the object if it is
 * non-empty, or null otherwise. Returns null on parse errors too.
 *
 * The payload field is stored as a JSON string in Redis and returned as-is
 * by the API; we parse it here at the point of display.
 */
function parsedPayload(raw: string): Record<string, unknown> | null {
  if (!raw) return null
  try {
    const p: unknown = JSON.parse(raw)
    if (typeof p === 'object' && p !== null && Object.keys(p).length > 0) {
      return p as Record<string, unknown>
    }
    return null
  } catch {
    return null
  }
}

export default function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!jobId) {
      setNotFound(true)
      setLoading(false)
      return
    }
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

  const payload = parsedPayload(job.payload)

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
      {payload !== null && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <h2 className="mb-3 text-sm font-medium text-zinc-400">Payload</h2>
          <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs text-zinc-300">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
