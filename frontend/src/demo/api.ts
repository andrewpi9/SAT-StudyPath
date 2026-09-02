/**
 * Drop-in replacement for the real api/ functions, backed by the in-browser
 * store and the ported engine. Same return shapes as the FastAPI responses.
 */

import type { BulkImportResult } from '../api/attempts'
import type { User } from '../api/auth'
import type { Progress } from '../api/progress'
import type {
  AttemptResult,
  Difficulty,
  MasteryOverview,
  Section,
  StudyPlan,
  StudyPlanItem,
  TopicMastery,
} from '../api/types'
import { DEMO_USER } from '../lib/demo'
import {
  COLD_START_MASTERY,
  confidenceFromAttempts,
  decayedMastery,
  daysSincePractice,
  evaluateTopic,
  rankTopics,
  readinessBySection,
  readinessSeries,
  type Recommendation,
  type TopicSnapshot,
  weightedReadiness,
} from '../lib/engine'
import { parseCsv } from './csv'
import { addAttempt, allAttempts, masteryByTopic, resources, topics } from './store'

const DAY_MS = 86_400_000
const delay = <T>(value: T) => new Promise<T>((resolve) => setTimeout(() => resolve(value), 120))

function snapshots(now: number): TopicSnapshot[] {
  const mastery = masteryByTopic(now)
  return topics.map((topic) => {
    const row = mastery.get(topic.id)
    return {
      topic_id: topic.id,
      section: topic.section,
      domain: topic.domain,
      skill_name: topic.skill_name,
      frequency_weight: topic.frequency_weight,
      mastery_score: row?.mastery_score ?? COLD_START_MASTERY,
      attempts_count: row?.attempts_count ?? 0,
      last_practiced: row?.last_practiced ?? null,
    }
  })
}

function toMastery(r: Recommendation): TopicMastery {
  return {
    topic_id: r.topic_id,
    skill_name: r.skill_name,
    section: r.section,
    domain: r.domain,
    frequency_weight: r.frequency_weight,
    mastery_score: r.mastery_score,
    decayed_mastery: r.decayed_mastery,
    confidence: r.confidence,
    attempts_count: r.attempts_count,
    last_practiced: r.last_practiced === null ? null : new Date(r.last_practiced).toISOString(),
    days_since_practice: r.days_since_practice,
  }
}

export function getMe(): Promise<User> {
  return delay(DEMO_USER)
}

export function getMastery(): Promise<MasteryOverview> {
  const now = Date.now()
  const snaps = snapshots(now)
  const scored = snaps
    .map((s) => evaluateTopic(s, now))
    .sort(
      (a, b) =>
        a.section.localeCompare(b.section) ||
        a.domain.localeCompare(b.domain) ||
        b.frequency_weight - a.frequency_weight ||
        a.skill_name.localeCompare(b.skill_name),
    )
  return delay({
    generated_at: new Date(now).toISOString(),
    overall_readiness: weightedReadiness(snaps, now),
    section_readiness: readinessBySection(snaps, now),
    topics: scored.map(toMastery),
  })
}

export function getStudyPlan(limit = 5): Promise<StudyPlan> {
  const now = Date.now()
  const items: StudyPlanItem[] = rankTopics(snapshots(now), now, limit).map((r) => ({
    ...toMastery(r),
    urgency: r.urgency,
    exploration_bonus: r.exploration_bonus,
    priority_score: r.priority_score,
    reason: r.reason,
    resources: resources.filter((res) => res.topic_id === r.topic_id),
  }))
  return delay({ generated_at: new Date(now).toISOString(), limit, items })
}

export function getProgress(days = 30): Promise<Progress> {
  const now = Date.now()
  const end = now
  const start = now - (days - 1) * DAY_MS
  const weights = new Map<number, { section: Section; weight: number }>(
    topics.map((t) => [t.id, { section: t.section, weight: t.frequency_weight }]),
  )
  const events = allAttempts(now).map((a) => ({
    topic_id: a.topic_id,
    correct: a.correct,
    at: a.at,
  }))
  const points = readinessSeries(weights, events, start, end).map((p) => ({
    day: p.day,
    overall_readiness: p.overall,
    math_readiness: p.by_section.Math ?? 0,
    reading_writing_readiness: p.by_section.ReadingWriting ?? 0,
  }))
  return delay({ range_days: days, points })
}

export function logAttempt(payload: {
  topic_id: number
  correct: boolean
  time_taken_seconds: number
  difficulty: Difficulty
}): Promise<AttemptResult> {
  const attempt = addAttempt(payload.topic_id, payload.correct, payload.difficulty)
  const now = Date.now()
  const topic = topics.find((t) => t.id === payload.topic_id)
  const row = masteryByTopic(now).get(payload.topic_id)
  const mastery_score = row?.mastery_score ?? COLD_START_MASTERY
  const attempts_count = row?.attempts_count ?? 0
  const last = row?.last_practiced ?? null

  const mastery: TopicMastery = {
    topic_id: payload.topic_id,
    skill_name: topic?.skill_name ?? '',
    section: topic?.section ?? 'Math',
    domain: topic?.domain ?? '',
    frequency_weight: topic?.frequency_weight ?? 0,
    mastery_score,
    decayed_mastery: decayedMastery(mastery_score, last, now),
    confidence: confidenceFromAttempts(attempts_count),
    attempts_count,
    last_practiced: last === null ? null : new Date(last).toISOString(),
    days_since_practice: daysSincePractice(last, now),
  }

  return delay({
    attempt: {
      id: attempt.at,
      topic_id: attempt.topic_id,
      correct: attempt.correct,
      time_taken_seconds: payload.time_taken_seconds,
      difficulty: attempt.difficulty,
      timestamp: new Date(attempt.at).toISOString(),
    },
    mastery,
  })
}

export function bulkImportAttempts(file: File): Promise<BulkImportResult> {
  return file.text().then((text) => {
    const { rows, errors } = parseCsv(text, topics)
    for (const row of rows) {
      addAttempt(row.topic_id, row.correct, row.difficulty)
    }
    return { imported: rows.length, failed: errors.length, errors }
  })
}
