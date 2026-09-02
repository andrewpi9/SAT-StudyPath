import { getMastery } from '../api/mastery'
import { getProgress } from '../api/progress'
import AsyncBoundary from '../components/AsyncBoundary'
import MasteryHeatmap from '../components/MasteryHeatmap'
import PageHeader from '../components/PageHeader'
import ReadinessSummary from '../components/ReadinessSummary'
import ReadinessTrend from '../components/ReadinessTrend'
import SeedPrompt from '../components/SeedPrompt'
import { useAsync } from '../hooks/useAsync'

export default function DashboardPage() {
  const mastery = useAsync(getMastery)
  const progress = useAsync(() => getProgress(30))

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Mastery Dashboard"
        subtitle="Effective mastery per skill after forgetting-curve decay."
      />

      <div className="mt-6">
        <AsyncBoundary
          state={mastery}
          empty={(data) => (data.topics.length === 0 ? <SeedPrompt /> : null)}
        >
          {(data) => (
            <div className="space-y-8">
              <ReadinessSummary data={data} />
              {progress.data && progress.data.points.length > 1 && (
                <ReadinessTrend points={progress.data.points} />
              )}
              <MasteryHeatmap topics={data.topics} />
            </div>
          )}
        </AsyncBoundary>
      </div>
    </main>
  )
}
