import { type MouseEvent, useState } from 'react'

import { type Section, SECTION_LABEL, type TopicMastery } from '../api/types'
import { BAND_ORDER, BANDS, masteryBand } from '../lib/masteryBand'

const SECTIONS: Section[] = ['Math', 'ReadingWriting']
const pct = (n: number) => `${Math.round(n * 100)}%`

interface Hover {
  topic: TopicMastery
  x: number
  y: number
}

function CellTooltip({ hover }: { hover: Hover }) {
  const { topic } = hover
  const decayed = pct(topic.decayed_mastery)
  const stored = pct(topic.mastery_score)
  return (
    <div
      className="pointer-events-none fixed z-50 max-w-[15rem] rounded-lg bg-slate-900 px-3 py-2 text-xs text-white shadow-lg dark:bg-slate-700"
      style={{
        left: Math.min(hover.x + 14, window.innerWidth - 250),
        top: hover.y + 14,
      }}
    >
      <p className="font-semibold">{topic.skill_name}</p>
      {topic.attempts_count === 0 ? (
        <p className="mt-0.5 text-slate-300">Not yet practiced</p>
      ) : (
        <div className="mt-0.5 space-y-0.5 text-slate-300">
          <p>{decayed === stored ? `Mastery ${stored}` : `Mastery ${decayed} (from ${stored})`}</p>
          <p>
            {topic.attempts_count} attempts · {topic.days_since_practice}d ago · confidence{' '}
            {pct(topic.confidence)}
          </p>
        </div>
      )}
    </div>
  )
}

function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600 dark:text-slate-400">
      {BAND_ORDER.map((key) => (
        <span key={key} className="flex items-center gap-1.5">
          <span
            className={
              key === 'untouched'
                ? 'inline-block h-3 w-3 rounded-sm border border-slate-300 bg-slate-100 dark:border-slate-600 dark:bg-slate-800'
                : 'inline-block h-3 w-3 rounded-sm'
            }
            style={key === 'untouched' ? undefined : { backgroundColor: BANDS[key].bg }}
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
  const [hover, setHover] = useState<Hover | null>(null)

  const track = (topic: TopicMastery) => (event: MouseEvent) =>
    setHover({ topic, x: event.clientX, y: event.clientY })

  return (
    <div className="space-y-6" onMouseLeave={() => setHover(null)}>
      <Legend />
      {SECTIONS.map((section) => {
        const sectionTopics = topics.filter((t) => t.section === section)
        if (sectionTopics.length === 0) return null
        return (
          <section key={section}>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
              {SECTION_LABEL[section]}
            </h2>
            <div className="mt-3 space-y-4">
              {byDomain(sectionTopics).map(([domain, domainTopics]) => {
                const avg = domainAverage(domainTopics)
                return (
                  <div key={domain}>
                    <h3 className="flex items-baseline gap-2 text-sm text-slate-700 dark:text-slate-300">
                      {domain}
                      {avg !== null && (
                        <span className="text-xs text-slate-400">avg {pct(avg)}</span>
                      )}
                    </h3>
                    <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-5">
                      {domainTopics.map((topic) => {
                        const untouched = topic.attempts_count === 0
                        const band = masteryBand(topic.decayed_mastery, topic.attempts_count)
                        return (
                          <div
                            key={topic.topic_id}
                            onMouseMove={track(topic)}
                            style={untouched ? undefined : { backgroundColor: band.bg, color: band.fg }}
                            className={[
                              'flex min-h-[76px] cursor-default flex-col justify-between rounded-lg p-2.5 transition-transform hover:scale-[1.02]',
                              untouched
                                ? 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
                                : '',
                            ].join(' ')}
                          >
                            <span className="text-[11px] font-medium leading-tight">
                              {topic.skill_name}
                            </span>
                            <span className="text-lg font-bold tabular-nums">
                              {untouched ? '—' : pct(topic.decayed_mastery)}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )
      })}

      {hover && <CellTooltip hover={hover} />}
    </div>
  )
}
