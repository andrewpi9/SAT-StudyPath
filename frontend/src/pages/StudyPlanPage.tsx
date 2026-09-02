import { Link } from 'react-router-dom'

import { getStudyPlan } from '../api/studyPlan'
import { SECTION_LABEL } from '../api/types'
import AsyncBoundary from '../components/AsyncBoundary'
import Card from '../components/Card'
import MasteryBar from '../components/MasteryBar'
import PageHeader from '../components/PageHeader'
import SeedPrompt from '../components/SeedPrompt'
import { useAsync } from '../hooks/useAsync'

export default function StudyPlanPage() {
  const state = useAsync(() => getStudyPlan(5))

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <PageHeader
        title="Today's Study Plan"
        subtitle="Ranked by how much test score is at risk right now — weak, high-frequency, or fading skills first."
      />

      <div className="mt-6">
        <AsyncBoundary
          state={state}
          empty={(plan) => (plan.items.length === 0 ? <SeedPrompt /> : null)}
        >
          {(plan) => (
            <ol className="space-y-3">
              {plan.items.map((item, index) => (
                <li key={item.topic_id}>
                  <Card className="p-4">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                        {index + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                          <h2 className="font-medium text-slate-900">{item.skill_name}</h2>
                          <span className="text-xs text-slate-400">
                            {SECTION_LABEL[item.section]} · {item.domain}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-slate-600">{item.reason}</p>
                        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                          <MasteryBar
                            mastery={item.decayed_mastery}
                            attempts={item.attempts_count}
                          />
                          <Link
                            to={`/log?topic=${item.topic_id}`}
                            className="shrink-0 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
                          >
                            Practice this →
                          </Link>
                        </div>
                      </div>
                    </div>
                  </Card>
                </li>
              ))}
            </ol>
          )}
        </AsyncBoundary>
      </div>
    </main>
  )
}
