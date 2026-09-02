import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'
import { getStudyPlan } from '../api/studyPlan'
import { SECTION_LABEL, type StudyPlan } from '../api/types'

const pct = (n: number) => `${Math.round(n * 100)}%`

export default function StudyPlanPage() {
  const [plan, setPlan] = useState<StudyPlan | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getStudyPlan(5)
      .then((p) => !cancelled && setPlan(p))
      .catch(
        (e) =>
          !cancelled &&
          setError(e instanceof ApiError ? `${e.status} · ${e.message}` : String(e)),
      )
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-xl font-semibold text-slate-900">Today's Study Plan</h1>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}

      {error && (
        <p className="mt-4 text-red-700">
          Couldn't load the study plan — {error}
          <br />
          <span className="text-sm text-slate-500">
            Is the API running on :8000, and has the database been seeded
            (<code>python -m app.seed</code>)?
          </span>
        </p>
      )}

      {plan && plan.items.length === 0 && (
        <p className="mt-4 text-slate-500">
          No topics yet — seed the database with <code>python -m app.seed</code>.
        </p>
      )}

      {plan && plan.items.length > 0 && (
        <>
          <p className="mt-1 text-sm text-slate-500">
            Top {plan.items.length}, ranked by priority.
          </p>
          <ol className="mt-4 space-y-3">
            {plan.items.map((item, i) => (
              <li
                key={item.topic_id}
                className="rounded border border-slate-300 p-4"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium text-slate-900">
                    {i + 1}. {item.skill_name}
                  </span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {SECTION_LABEL[item.section]} · {item.domain}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-700">{item.reason}</p>
                <p className="mt-2 text-xs text-slate-400">
                  priority {item.priority_score.toFixed(3)} · mastery{' '}
                  {pct(item.decayed_mastery)} · {item.attempts_count} attempts
                </p>
              </li>
            ))}
          </ol>
        </>
      )}
    </main>
  )
}
