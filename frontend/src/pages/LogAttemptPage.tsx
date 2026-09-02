import { type FormEvent, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { logAttempt } from '../api/attempts'
import { ApiError } from '../api/client'
import { getMastery } from '../api/mastery'
import { type Difficulty, type Section, SECTION_LABEL, type TopicMastery } from '../api/types'
import { useAsync } from '../hooks/useAsync'

const SECTIONS: Section[] = ['Math', 'ReadingWriting']
const DIFFICULTIES: Difficulty[] = ['easy', 'medium', 'hard']
const pct = (n: number) => `${Math.round(n * 100)}%`

interface LoggedRow {
  key: number
  skill: string
  correct: boolean
  before: number
  after: number
  attempts: number
}

export default function LogAttemptPage() {
  const { data, error, loading } = useAsync(getMastery)

  // Mastery values we've changed by logging attempts this session, layered over
  // the fetched snapshot so the dropdown and "current" line stay accurate.
  const [overrides, setOverrides] = useState<Record<number, TopicMastery>>({})
  const [log, setLog] = useState<LoggedRow[]>([])

  const [topicId, setTopicId] = useState<number | ''>('')
  const [correct, setCorrect] = useState<boolean | null>(null)
  const [seconds, setSeconds] = useState(60)
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const topics = useMemo(
    () => (data ? data.topics.map((t) => overrides[t.topic_id] ?? t) : []),
    [data, overrides],
  )
  const selected = topics.find((t) => t.topic_id === topicId) ?? null

  async function submit(event: FormEvent) {
    event.preventDefault()
    setFormError(null)
    if (topicId === '' || correct === null) {
      setFormError('Pick a topic and an outcome.')
      return
    }

    const before = selected ? selected.decayed_mastery : 0
    setSubmitting(true)
    try {
      const result = await logAttempt({
        topic_id: topicId,
        correct,
        time_taken_seconds: seconds,
        difficulty,
      })
      setOverrides((current) => ({ ...current, [result.mastery.topic_id]: result.mastery }))
      setLog((rows) => [
        {
          key: result.attempt.id,
          skill: result.mastery.skill_name,
          correct,
          before,
          after: result.mastery.decayed_mastery,
          attempts: result.mastery.attempts_count,
        },
        ...rows,
      ])
      setCorrect(null)
    } catch (err) {
      setFormError(err instanceof ApiError ? `${err.status} · ${err.message}` : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto max-w-xl p-6">
      <h1 className="text-xl font-semibold text-slate-900">Log a Practice Attempt</h1>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && (
        <p className="mt-4 text-red-700">
          Couldn't load topics — {error}
        </p>
      )}

      {data && (
        <form onSubmit={submit} className="mt-4 space-y-4">
          <label className="block">
            <span className="text-sm text-slate-700">Topic</span>
            <select
              value={topicId}
              onChange={(e) => setTopicId(e.target.value === '' ? '' : Number(e.target.value))}
              className="mt-1 block w-full rounded border border-slate-300 p-2"
            >
              <option value="">Select a topic…</option>
              {SECTIONS.map((section) => (
                <optgroup key={section} label={SECTION_LABEL[section]}>
                  {topics
                    .filter((t) => t.section === section)
                    .map((t) => (
                      <option key={t.topic_id} value={t.topic_id}>
                        {t.skill_name} —{' '}
                        {t.attempts_count === 0 ? 'not started' : pct(t.decayed_mastery)}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            {selected && (
              <span className="mt-1 block text-xs text-slate-500">
                Current:{' '}
                {selected.attempts_count === 0
                  ? 'not started'
                  : `${pct(selected.decayed_mastery)} mastery · ${selected.attempts_count} attempts`}
              </span>
            )}
          </label>

          <fieldset>
            <legend className="text-sm text-slate-700">Outcome</legend>
            <div className="mt-1 flex gap-2">
              {[
                { value: true, label: 'Correct' },
                { value: false, label: 'Incorrect' },
              ].map(({ value, label }) => (
                <button
                  key={label}
                  type="button"
                  aria-pressed={correct === value}
                  onClick={() => setCorrect(value)}
                  className={[
                    'rounded border px-3 py-1.5 text-sm',
                    correct === value
                      ? 'border-slate-900 bg-slate-900 text-white'
                      : 'border-slate-300 text-slate-700 hover:bg-slate-50',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="block">
            <span className="text-sm text-slate-700">Time taken (seconds)</span>
            <input
              type="number"
              min={1}
              max={3600}
              value={seconds}
              onChange={(e) => setSeconds(Number(e.target.value))}
              className="mt-1 block w-28 rounded border border-slate-300 p-2"
            />
          </label>

          <label className="block">
            <span className="text-sm text-slate-700">Difficulty</span>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as Difficulty)}
              className="mt-1 block w-full rounded border border-slate-300 p-2"
            >
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>
                  {d[0].toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
          </label>

          {formError && <p className="text-sm text-red-700">{formError}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {submitting ? 'Logging…' : 'Log attempt'}
          </button>
        </form>
      )}

      {log.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-slate-700">Logged this session</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {log.map((row) => (
              <li key={row.key} className="flex flex-wrap items-center gap-x-2">
                <span className={row.correct ? 'text-green-700' : 'text-red-600'}>
                  {row.correct ? '✓' : '✗'}
                </span>
                <span className="text-slate-900">{row.skill}</span>
                <span className="text-slate-500">
                  {pct(row.before)} → {pct(row.after)} · {row.attempts} attempts
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            <Link to="/dashboard" className="underline">
              See it on the dashboard
            </Link>
          </p>
        </section>
      )}
    </main>
  )
}
