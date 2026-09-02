import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'
import BrandMark from './components/BrandMark'
import ThemeToggle from './components/ThemeToggle'
import DashboardPage from './pages/DashboardPage'
import LogAttemptPage from './pages/LogAttemptPage'
import LoginPage from './pages/LoginPage'
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
      ? 'border-indigo-600 text-slate-900 dark:border-indigo-400 dark:text-slate-100'
      : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800 dark:text-slate-400 dark:hover:border-slate-700 dark:hover:text-slate-200',
  ].join(' ')

function AuthedApp() {
  const { user, logout } = useAuth()
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-8 gap-y-3 px-6 pt-4">
            <div className="flex items-center gap-2">
              <BrandMark />
              <span className="font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                SAT StudyPath
              </span>
            </div>
            <nav className="flex gap-6">
              {NAV.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto flex items-center gap-3 pb-3">
              <ThemeToggle />
              <span className="hidden text-sm text-slate-500 dark:text-slate-400 sm:inline">
                {user?.email}
              </span>
              <button
                type="button"
                onClick={logout}
                className="text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              >
                Log out
              </button>
            </div>
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

function Gate() {
  const { status } = useAuth()
  if (status === 'loading') {
    return <p className="p-16 text-sm text-slate-500 dark:text-slate-400">Loading…</p>
  }
  return status === 'authenticated' ? <AuthedApp /> : <LoginPage />
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
