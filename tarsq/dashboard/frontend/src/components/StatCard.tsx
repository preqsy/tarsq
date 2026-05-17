type StatColor = 'zinc' | 'amber' | 'blue' | 'emerald' | 'red'

const VALUE_COLOR: Record<StatColor, string> = {
  zinc:    'text-zinc-100',
  amber:   'text-amber-400',
  blue:    'text-blue-400',
  emerald: 'text-emerald-400',
  red:     'text-red-400',
}

interface StatCardProps {
  label: string
  value: string
  color?: StatColor
}

export default function StatCard({ label, value, color = 'zinc' }: StatCardProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${VALUE_COLOR[color]}`}>
        {value}
      </p>
    </div>
  )
}
