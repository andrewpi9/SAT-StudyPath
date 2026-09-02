import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'

import DashboardPage from './pages/DashboardPage'
import LogAttemptPage from './pages/LogAttemptPage'
import StudyPlanPage from './pages/StudyPlanPage'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'px-3 py-2 text-sm border-b-2 -mb-px',
    isActive
      ? 'border-slate-900 font-semibold text-slate-900'
      : 'border-transparent text-slate-500 hover:text-slate-700',
  ].join(' ')

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-white">
        <header className="px-6 pt-5">
          <span className="text-sm font-semibold tracking-tight text-slate-900">
            SAT StudyPath
          </span>
        </header>
        <nav className="flex gap-1 border-b border-slate-200 px-6">
          <NavLink to="/" end className={navLinkClass}>
            Study Plan
          </NavLink>
          <NavLink to="/dashboard" className={navLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/log" className={navLinkClass}>
            Log Attempt
          </NavLink>
        </nav>
        <Routes>
          <Route path="/" element={<StudyPlanPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/log" element={<LogAttemptPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
