import { useState, useEffect } from 'react'
import { api } from '../api'
import type { Schedule } from '../types'

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load(): Promise<void> {
      try {
        const data = await api.schedules()
        setSchedules(data.schedules)
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    void load()
    const id = setInterval(() => { void load() }, 30_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Schedules</h1>
        <p className="mt-0.5 text-sm text-zinc-500">
          {schedules.length} registered cron schedule{schedules.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 rounded-lg bg-zinc-800/50 animate-pulse" />
            ))}
          </div>
        ) : schedules.length === 0 ? (
          <p className="py-12 text-center text-sm text-zinc-600">
            No schedules registered
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  {['Name', 'Cron Expression', 'Last Run', 'Next Run'].map((h) => (
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
                {schedules.map((s) => (
                  <tr key={s.name}>
                    <td className="py-3 pr-4 font-medium text-zinc-200">{s.name}</td>
                    <td className="py-3 pr-4">
                      <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-xs text-zinc-400">
                        {s.cron}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-xs text-zinc-500">{fmt(s.last_run)}</td>
                    <td className="py-3 text-xs text-zinc-400">{fmt(s.next_run)}</td>
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
