import { getMastery } from '../api/mastery'
import MasteryHeatmap from '../components/MasteryHeatmap'
import ReadinessSummary from '../components/ReadinessSummary'
import { useAsync } from '../hooks/useAsync'

export default function DashboardPage() {
  const { data, error, loading } = useAsync(getMastery)

  return (
    <main className="mx-auto max-w-4xl p-6">
      <h1 className="text-xl font-semibold text-slate-900">Mastery Dashboard</h1>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}

      {error && (
        <p className="mt-4 text-red-700">
          Couldn't load mastery data — {error}
          <br />
          <span className="text-sm text-slate-500">
            Is the API running on :8000, and has the database been seeded?
          </span>
        </p>
      )}

      {data && data.topics.length === 0 && (
        <p className="mt-4 text-slate-500">
          No topics yet — seed the database with <code>python -m app.seed</code>.
        </p>
      )}

      {data && data.topics.length > 0 && (
        <>
          <p className="mt-1 text-sm text-slate-500">
            Effective mastery after forgetting-curve decay, by skill.
          </p>
          <div className="mt-4">
            <ReadinessSummary data={data} />
          </div>
          <div className="mt-8">
            <MasteryHeatmap topics={data.topics} />
          </div>
        </>
      )}
    </main>
  )
}
