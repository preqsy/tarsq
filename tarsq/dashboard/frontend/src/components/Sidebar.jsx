import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Briefcase, Cpu, Clock } from 'lucide-react'

const nav = [
  { to: '/overview', label: 'Overview', Icon: LayoutDashboard },
  { to: '/jobs', label: 'Jobs', Icon: Briefcase },
  { to: '/workers', label: 'Workers', Icon: Cpu },
  { to: '/schedules', label: 'Schedules', Icon: Clock },
]

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-zinc-800 px-4 py-4">
        <svg viewBox="0 0 22 22" fill="none" width={22} height={22}>
          <path d="M3 5 L11 1 L19 5 L19 17 L11 21 L3 17 Z" stroke="#c6ff3d" strokeWidth="1.6" strokeLinejoin="round"/>
          <path d="M7 9 L11 11 L15 9 M11 11 L11 16" stroke="#c6ff3d" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <div>
          <p className="text-sm font-semibold text-zinc-100">Tarsq</p>
          <p className="text-xs text-zinc-600">Task Queue</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-3">
        {nav.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-500/15 text-indigo-400'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-zinc-800 px-4 py-3">
        <p className="text-xs text-zinc-600">Dashboard v0.1.0</p>
      </div>
    </aside>
  )
}
