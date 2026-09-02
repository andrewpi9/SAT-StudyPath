import { getMastery } from '../api/mastery'
import AsyncBoundary from '../components/AsyncBoundary'
import MasteryHeatmap from '../components/MasteryHeatmap'
import PageHeader from '../components/PageHeader'
import ReadinessSummary from '../components/ReadinessSummary'
import SeedPrompt from '../components/SeedPrompt'
import { useAsync } from '../hooks/useAsync'

export default function DashboardPage() {
  const state = useAsync(getMastery)

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Mastery Dashboard"
        subtitle="Effective mastery per skill after forgetting-curve decay."
      />

      <div className="mt-6">
        <AsyncBoundary
          state={state}
          empty={(data) => (data.topics.length === 0 ? <SeedPrompt /> : null)}
        >
          {(data) => (
            <div className="space-y-8">
              <ReadinessSummary data={data} />
              <MasteryHeatmap topics={data.topics} />
            </div>
          )}
        </AsyncBoundary>
      </div>
    </main>
  )
}
