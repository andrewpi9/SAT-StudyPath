import { type ChangeEvent, useState } from 'react'

import { type BulkImportResult, bulkImportAttempts, CSV_TEMPLATE_URL } from '../api/attempts'
import { ApiError } from '../api/client'
import Card from './Card'

export default function CsvImport({ onImported }: { onImported: () => void }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<BulkImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // allow re-selecting the same file
    if (!file) return

    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const res = await bulkImportAttempts(file)
      setResult(res)
      if (res.imported > 0) onImported()
    } catch (err) {
      setError(err instanceof ApiError ? `${err.status} · ${err.message}` : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        Bulk import (CSV)
      </h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Columns: <code>topic, correct</code> (required),{' '}
        <code>time_taken_seconds, difficulty, days_ago</code> (optional).{' '}
        <a
          href={CSV_TEMPLATE_URL}
          className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
        >
          Download template
        </a>
      </p>

      <label className="mt-3 inline-flex cursor-pointer items-center rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
        {busy ? 'Importing…' : 'Choose CSV file'}
        <input
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          disabled={busy}
          onChange={handleFile}
        />
      </label>

      {error && <p className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {result && (
        <div className="mt-3 text-sm">
          <p className="text-slate-700 dark:text-slate-300">
            Imported <span className="font-semibold">{result.imported}</span>
            {result.failed > 0 && (
              <>
                {' '}
                ·{' '}
                <span className="font-semibold text-red-600 dark:text-red-400">
                  {result.failed} skipped
                </span>
              </>
            )}
          </p>
          {result.errors.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs text-red-700 dark:text-red-400">
              {result.errors.slice(0, 8).map((e) => (
                <li key={e.row}>
                  Row {e.row}: {e.message}
                </li>
              ))}
              {result.errors.length > 8 && (
                <li className="text-slate-500 dark:text-slate-400">
                  …and {result.errors.length - 8} more
                </li>
              )}
            </ul>
          )}
        </div>
      )}
    </Card>
  )
}
