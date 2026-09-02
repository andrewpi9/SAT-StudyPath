import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'

import DashboardPage from './pages/DashboardPage'
import LogAttemptPage from './pages/LogAttemptPage'
import StudyPlanPage from './pages/StudyPlanPage'

const NAV = [
  { to: '/', label: 'Study Plan', end: true },
  { to: '/dashboard', label: 'Dashboard', end: false },
  { to: '/log', label: 'Log Attempt', end: false },
]

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'inline-flex items-center border-b-2 px-1 pb-3 pt-1 text-sm font-medium transition-colors',
    isActive
      ? 'border-indigo-600 text-slate-900'
      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800',
  ].join(' ')

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" className="h-6 w-6" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#4f46e5" />
      <rect x="7" y="17" width="4.5" height="8" rx="1.2" fill="#fff" opacity="0.55" />
      <rect x="13.75" y="12" width="4.5" height="13" rx="1.2" fill="#fff" opacity="0.8" />
      <rect x="20.5" y="7" width="4.5" height="18" rx="1.2" fill="#fff" />
    </svg>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 pt-4 sm:flex-row sm:items-center sm:gap-8">
            <div className="flex items-center gap-2">
              <BrandMark />
              <span className="font-semibold tracking-tight text-slate-900">SAT StudyPath</span>
            </div>
            <nav className="flex gap-6">
              {NAV.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>

        <Routes>
          <Route path="/" element={<StudyPlanPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/log" element={<LogAttemptPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
