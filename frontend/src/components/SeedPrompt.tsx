import { useState } from 'react'

import { api } from '../api/client'

/** Empty-state call to action: populate the current account from the browser. */
export default function SeedPrompt() {
  const [status, setStatus] = useState<'idle' | 'seeding' | 'error'>('idle')

  async function seed() {
    setStatus('seeding')
    try {
      await api.post('/topics/seed', { rng_seed: 42 })
      window.location.reload()
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-900">
      <p className="font-medium text-slate-800 dark:text-slate-200">No practice data yet</p>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Load a synthetic ~4-week practice history to explore the app.
      </p>
      <button
        type="button"
        onClick={seed}
        disabled={status === 'seeding'}
        className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
      >
        {status === 'seeding' ? 'Loading…' : 'Load demo data'}
      </button>
      {status === 'error' && (
        <p className="mt-2 text-sm text-red-700 dark:text-red-400">
          Couldn&rsquo;t reach the API — is the backend running?
        </p>
      )}
    </div>
  )
}
