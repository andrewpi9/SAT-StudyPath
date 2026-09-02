import { type FormEvent, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { logAttempt } from '../api/attempts'
import { ApiError } from '../api/client'
import { getMastery } from '../api/mastery'
import { type Difficulty, type Section, SECTION_LABEL, type TopicMastery } from '../api/types'
import AsyncBoundary from '../components/AsyncBoundary'
import Card from '../components/Card'
import PageHeader from '../components/PageHeader'
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

const fieldLabel = 'block text-sm font-medium text-slate-700'
const fieldInput =
  'mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

export default function LogAttemptPage() {
  const state = useAsync(getMastery)
  const [searchParams] = useSearchParams()

  const [overrides, setOverrides] = useState<Record<number, TopicMastery>>({})
  const [log, setLog] = useState<LoggedRow[]>([])

  const [topicId, setTopicId] = useState<number | ''>(Number(searchParams.get('topic')) || '')
  const [correct, setCorrect] = useState<boolean | null>(null)
  const [seconds, setSeconds] = useState(60)
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const topics = useMemo(
    () => (state.data ? state.data.topics.map((t) => overrides[t.topic_id] ?? t) : []),
    [state.data, overrides],
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
    <main className="mx-auto max-w-xl px-6 py-8">
      <PageHeader
        title="Log a Practice Attempt"
        subtitle="Record one question outcome; mastery updates immediately."
      />

      <div className="mt-6 space-y-6">
        <AsyncBoundary state={state}>
          {() => (
            <Card className="p-5">
              <form onSubmit={submit} className="space-y-4">
                <label className={fieldLabel}>
                  Topic
                  <select
                    value={topicId}
                    onChange={(e) =>
                      setTopicId(e.target.value === '' ? '' : Number(e.target.value))
                    }
                    className={fieldInput}
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
                    <span className="mt-1 block text-xs font-normal text-slate-500">
                      Current:{' '}
                      {selected.attempts_count === 0
                        ? 'not started'
                        : `${pct(selected.decayed_mastery)} mastery · ${selected.attempts_count} attempts`}
                    </span>
                  )}
                </label>

                <fieldset>
                  <legend className={fieldLabel}>Outcome</legend>
                  <div className="mt-1 inline-flex rounded-lg border border-slate-300 p-0.5">
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
                          'rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                          correct === value
                            ? 'bg-slate-900 text-white'
                            : 'text-slate-600 hover:text-slate-900',
                        ].join(' ')}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </fieldset>

                <div className="flex gap-4">
                  <label className={`${fieldLabel} flex-1`}>
                    Time (seconds)
                    <input
                      type="number"
                      min={1}
                      max={3600}
                      value={seconds}
                      onChange={(e) => setSeconds(Number(e.target.value))}
                      className={fieldInput}
                    />
                  </label>
                  <label className={`${fieldLabel} flex-1`}>
                    Difficulty
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value as Difficulty)}
                      className={fieldInput}
                    >
                      {DIFFICULTIES.map((d) => (
                        <option key={d} value={d}>
                          {d[0].toUpperCase() + d.slice(1)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {formError && <p className="text-sm text-red-700">{formError}</p>}

                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {submitting ? 'Logging…' : 'Log attempt'}
                </button>
              </form>
            </Card>
          )}
        </AsyncBoundary>

        {log.length > 0 && (
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-slate-700">Logged this session</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {log.map((row) => (
                <li key={row.key} className="flex flex-wrap items-center gap-x-2">
                  <span
                    className={
                      row.correct
                        ? 'font-semibold text-green-600'
                        : 'font-semibold text-red-500'
                    }
                  >
                    {row.correct ? '✓' : '✗'}
                  </span>
                  <span className="text-slate-900">{row.skill}</span>
                  <span className="tabular-nums text-slate-500">
                    {pct(row.before)} → {pct(row.after)} · {row.attempts} attempts
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-slate-500">
              <Link to="/dashboard" className="font-medium text-indigo-600 hover:underline">
                See it on the dashboard →
              </Link>
            </p>
          </Card>
        )}
      </div>
    </main>
  )
}
