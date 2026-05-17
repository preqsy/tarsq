const STYLES = {
  queued:      'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  in_progress: 'bg-blue-500/10 text-blue-400 ring-blue-500/20',
  completed:   'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20',
  failed:      'bg-red-500/10 text-red-400 ring-red-500/20',
}

const LABELS = {
  queued:      'Queued',
  in_progress: 'In Progress',
  completed:   'Completed',
  failed:      'Failed',
}

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
        STYLES[status] ?? 'bg-zinc-500/10 text-zinc-400 ring-zinc-500/20'
      }`}
    >
      {LABELS[status] ?? status}
    </span>
  )
}
