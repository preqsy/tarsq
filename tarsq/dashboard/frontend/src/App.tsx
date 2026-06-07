import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Overview from './views/Overview'
import Jobs from './views/Jobs'
import Workers from './views/Workers'
import Schedules from './views/Schedules'
import JobDetail from './views/JobDetail'

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-8 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/jobs/:jobId" element={<JobDetail />} />
            <Route path="/workers" element={<Workers />} />
            <Route path="/schedules" element={<Schedules />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}
