import { type FormEvent, useState } from 'react'

import { DEMO_CREDENTIALS } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'
import BrandMark from '../components/BrandMark'
import Card from '../components/Card'

const field =
  'mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

export default function LoginPage() {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run(action: Promise<void>) {
    setBusy(true)
    setError(null)
    try {
      await action
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
      setBusy(false)
    }
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    void run(mode === 'login' ? login(email, password) : signup(email, password))
  }

  return (
    <div className="mx-auto max-w-sm px-6 py-16">
      <div className="flex items-center justify-center gap-2">
        <BrandMark />
        <span className="font-semibold tracking-tight text-slate-900">SAT StudyPath</span>
      </div>

      <Card className="mt-6 p-6">
        <h1 className="text-lg font-semibold text-slate-900">
          {mode === 'login' ? 'Log in' : 'Create an account'}
        </h1>

        <form onSubmit={submit} className="mt-4 space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={field}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Password
            <input
              type="password"
              required
              minLength={8}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={field}
            />
          </label>

          {error && <p className="text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? '…' : mode === 'login' ? 'Log in' : 'Sign up'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => setMode((m) => (m === 'login' ? 'signup' : 'login'))}
          className="mt-3 text-sm text-indigo-600 hover:underline"
        >
          {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Log in'}
        </button>

        <div className="mt-5 border-t border-slate-200 pt-4">
          <button
            type="button"
            disabled={busy}
            onClick={() => void run(login(DEMO_CREDENTIALS.email, DEMO_CREDENTIALS.password))}
            className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Try the demo account
          </button>
          <p className="mt-2 text-center text-xs text-slate-400">
            Pre-loaded with a ~4-week practice history.
          </p>
        </div>
      </Card>
    </div>
  )
}
