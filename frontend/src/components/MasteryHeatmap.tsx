import { type Section, SECTION_LABEL, type TopicMastery } from '../api/types'
import { BAND_ORDER, BANDS, masteryBand } from '../lib/masteryBand'

const SECTIONS: Section[] = ['Math', 'ReadingWriting']
const pct = (n: number) => `${Math.round(n * 100)}%`

function cellTooltip(t: TopicMastery): string {
  const lines = [t.skill_name]
  if (t.attempts_count === 0) {
    lines.push('Not yet practiced')
  } else {
    lines.push(
      Math.round(t.decayed_mastery * 100) === Math.round(t.mastery_score * 100)
        ? `Mastery ${pct(t.mastery_score)}`
        : `Mastery ${pct(t.decayed_mastery)} (decayed from ${pct(t.mastery_score)})`,
      `${t.attempts_count} attempts · last practiced ${t.days_since_practice}d ago`,
      `Confidence ${pct(t.confidence)}`,
    )
  }
  return lines.join('\n')
}

function Cell({ topic }: { topic: TopicMastery }) {
  const band = masteryBand(topic.decayed_mastery, topic.attempts_count)
  return (
    <div
      title={cellTooltip(topic)}
      style={{ backgroundColor: band.bg, color: band.fg }}
      className="flex min-h-[76px] flex-col justify-between rounded-lg p-2.5"
    >
      <span className="text-[11px] font-medium leading-tight">{topic.skill_name}</span>
      <span className="text-lg font-bold tabular-nums">
        {topic.attempts_count === 0 ? '—' : pct(topic.decayed_mastery)}
      </span>
    </div>
  )
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600">
      {BAND_ORDER.map((key) => (
        <span key={key} className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: BANDS[key].bg }}
          />
          {BANDS[key].label}
        </span>
      ))}
    </div>
  )
}

/** Consecutive-group the (already section/domain-sorted) topic list. */
function byDomain(topics: TopicMastery[]): [string, TopicMastery[]][] {
  const groups: [string, TopicMastery[]][] = []
  for (const topic of topics) {
    const last = groups.at(-1)
    if (last && last[0] === topic.domain) last[1].push(topic)
    else groups.push([topic.domain, [topic]])
  }
  return groups
}

function domainAverage(topics: TopicMastery[]): number | null {
  const practised = topics.filter((t) => t.attempts_count > 0)
  if (practised.length === 0) return null
  return practised.reduce((sum, t) => sum + t.decayed_mastery, 0) / practised.length
}

export default function MasteryHeatmap({ topics }: { topics: TopicMastery[] }) {
  return (
    <div className="space-y-6">
      <Legend />
      {SECTIONS.map((section) => {
        const sectionTopics = topics.filter((t) => t.section === section)
        if (sectionTopics.length === 0) return null
        return (
          <section key={section}>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {SECTION_LABEL[section]}
            </h2>
            <div className="mt-3 space-y-4">
              {byDomain(sectionTopics).map(([domain, domainTopics]) => {
                const avg = domainAverage(domainTopics)
                return (
                  <div key={domain}>
                    <h3 className="flex items-baseline gap-2 text-sm text-slate-700">
                      {domain}
                      {avg !== null && (
                        <span className="text-xs text-slate-400">avg {pct(avg)}</span>
                      )}
                    </h3>
                    <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-5">
                      {domainTopics.map((topic) => (
                        <Cell key={topic.topic_id} topic={topic} />
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )
      })}
    </div>
  )
}
