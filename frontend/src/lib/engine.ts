/**
 * The recommendation engine, ported from backend/app/algorithm/ so the static
 * demo can run the whole thing in the browser with no server.
 *
 * Same math as the Python. Timestamps are epoch milliseconds and "now" is
 * always passed in, so nothing here reads the clock on its own.
 */

import { type Section, SECTION_LABEL } from '../api/types'

export const LEARNING_RATE = 0.3
export const COLD_START_MASTERY = 0.4
export const CONFIDENCE_FULL_AT = 5
export const DECAY_RATE = 0.02
export const EXPLORATION_WEIGHT = 0.15

const DAY_MS = 86_400_000

// --- mastery: exponentially weighted moving average -------------------------

export function updateMastery(old: number, correct: boolean, lr = LEARNING_RATE): number {
  const outcome = correct ? 1 : 0
  return old + lr * (outcome - old)
}

export function confidenceFromAttempts(attempts: number, fullAt = CONFIDENCE_FULL_AT): number {
  if (attempts <= 0) return 0
  return Math.min(1, attempts / fullAt)
}

// --- forgetting curve decay ------------------------------------------------

export function daysSincePractice(lastPracticed: number | null, now: number): number | null {
  if (lastPracticed === null) return null
  return Math.max(0, Math.floor((now - lastPracticed) / DAY_MS))
}

export function decayedMastery(
  score: number,
  lastPracticed: number | null,
  now: number,
  rate = DECAY_RATE,
): number {
  const elapsed = daysSincePractice(lastPracticed, now)
  if (!elapsed) return score // never practiced, or practiced today
  return score * Math.exp(-rate * elapsed)
}

// --- priority ranking -----------------------------------------------------

export interface TopicSnapshot {
  topic_id: number
  section: Section
  domain: string
  skill_name: string
  frequency_weight: number
  mastery_score: number
  attempts_count: number
  last_practiced: number | null
}

export interface Recommendation extends TopicSnapshot {
  days_since_practice: number | null
  decayed_mastery: number
  confidence: number
  urgency: number
  exploration_bonus: number
  priority_score: number
  reason: string
}

export function explorationBonus(attempts: number, weight = EXPLORATION_WEIGHT): number {
  return weight / (1 + attempts)
}

function formatRecency(days: number | null): string {
  if (days === null) return 'not practiced yet'
  if (days === 0) return 'last practiced today'
  if (days === 1) return 'last practiced yesterday'
  return `last practiced ${days} days ago`
}

export function buildReason(args: {
  section: Section
  frequency_weight: number
  mastery_score: number
  decayed_mastery: number
  attempts_count: number
  days_elapsed: number | null
}): string {
  const freqPct = Math.round(args.frequency_weight * 100)
  const freqPart = `appears in ~${freqPct}% of the ${SECTION_LABEL[args.section]} section`

  if (args.attempts_count === 0) {
    return `Not yet practiced · ${freqPart} · exploration pick`
  }

  const earned = Math.round(args.mastery_score * 100)
  const nowPct = Math.round(args.decayed_mastery * 100)
  const masteryPart =
    nowPct === earned ? `Mastery ${earned}%` : `Mastery ${nowPct}% (decayed from ${earned}%)`

  return `${masteryPart} · ${freqPart} · ${formatRecency(args.days_elapsed)}`
}

export function evaluateTopic(s: TopicSnapshot, now: number): Recommendation {
  const elapsed = daysSincePractice(s.last_practiced, now)
  const decayed = decayedMastery(s.mastery_score, s.last_practiced, now)
  const urgency = 1 - decayed
  const bonus = explorationBonus(s.attempts_count)

  return {
    ...s,
    days_since_practice: elapsed,
    decayed_mastery: decayed,
    confidence: confidenceFromAttempts(s.attempts_count),
    urgency,
    exploration_bonus: bonus,
    priority_score: s.frequency_weight * urgency + bonus,
    reason: buildReason({
      section: s.section,
      frequency_weight: s.frequency_weight,
      mastery_score: s.mastery_score,
      decayed_mastery: decayed,
      attempts_count: s.attempts_count,
      days_elapsed: elapsed,
    }),
  }
}

export function rankTopics(
  snapshots: TopicSnapshot[],
  now: number,
  limit?: number,
): Recommendation[] {
  const ranked = snapshots
    .map((s) => evaluateTopic(s, now))
    .sort(
      (a, b) =>
        b.priority_score - a.priority_score ||
        b.frequency_weight - a.frequency_weight ||
        a.skill_name.localeCompare(b.skill_name),
    )
  return limit === undefined ? ranked : ranked.slice(0, limit)
}

// --- readiness roll-up --------------------------------------------------

export function weightedReadiness(snapshots: TopicSnapshot[], now: number): number {
  const totalWeight = snapshots.reduce((sum, s) => sum + s.frequency_weight, 0)
  if (totalWeight === 0) return 0
  const earned = snapshots.reduce(
    (sum, s) => sum + s.frequency_weight * decayedMastery(s.mastery_score, s.last_practiced, now),
    0,
  )
  return earned / totalWeight
}

export function readinessBySection(
  snapshots: TopicSnapshot[],
  now: number,
): Record<Section, number> {
  const out = {} as Record<Section, number>
  for (const section of ['Math', 'ReadingWriting'] as Section[]) {
    const items = snapshots.filter((s) => s.section === section)
    if (items.length > 0) out[section] = weightedReadiness(items, now)
  }
  return out
}

// --- readiness over time, replayed from the attempt log -----------------

export interface AttemptEvent {
  topic_id: number
  correct: boolean
  at: number
}

export interface ReadinessPoint {
  day: string // YYYY-MM-DD
  overall: number
  by_section: Record<Section, number>
}

interface ReplayState {
  section: Section
  weight: number
  mastery: number
  last: number | null
}

export function readinessSeries(
  topicWeights: Map<number, { section: Section; weight: number }>,
  events: AttemptEvent[],
  startMs: number,
  endMs: number,
): ReadinessPoint[] {
  const state = new Map<number, ReplayState>()
  for (const [id, { section, weight }] of topicWeights) {
    state.set(id, { section, weight, mastery: COLD_START_MASTERY, last: null })
  }

  const ordered = [...events].sort((a, b) => a.at - b.at)
  let cursor = 0
  const points: ReadinessPoint[] = []

  const firstDay = new Date(startMs)
  firstDay.setUTCHours(0, 0, 0, 0)
  const lastDay = new Date(endMs)
  lastDay.setUTCHours(0, 0, 0, 0)

  for (let d = firstDay.getTime(); d <= lastDay.getTime(); d += DAY_MS) {
    const cutoff = d + DAY_MS - 1
    while (cursor < ordered.length && ordered[cursor].at <= cutoff) {
      const event = ordered[cursor]
      const topic = state.get(event.topic_id)
      if (topic) {
        topic.mastery = updateMastery(topic.mastery, event.correct)
        if (topic.last === null || event.at > topic.last) topic.last = event.at
      }
      cursor += 1
    }

    const sectionEarned = {} as Record<Section, number>
    const sectionWeight = {} as Record<Section, number>
    for (const topic of state.values()) {
      const eff = decayedMastery(topic.mastery, topic.last, cutoff)
      sectionEarned[topic.section] = (sectionEarned[topic.section] ?? 0) + topic.weight * eff
      sectionWeight[topic.section] = (sectionWeight[topic.section] ?? 0) + topic.weight
    }

    const bySection = {} as Record<Section, number>
    let totalWeight = 0
    let totalEarned = 0
    for (const section of Object.keys(sectionWeight) as Section[]) {
      bySection[section] = sectionEarned[section] / sectionWeight[section]
      totalWeight += sectionWeight[section]
      totalEarned += sectionEarned[section]
    }

    points.push({
      day: new Date(d).toISOString().slice(0, 10),
      overall: totalWeight > 0 ? totalEarned / totalWeight : 0,
      by_section: bySection,
    })
  }

  return points
}
