/**
 * In-browser state for the demo. Seed history plus anything the visitor adds,
 * kept in localStorage so it survives a refresh. Everything the UI reads is
 * derived from this by replaying it through the engine, the same way the real
 * backend derives it from the database.
 */

import type { Difficulty, Section } from '../api/types'
import { COLD_START_MASTERY, updateMastery } from '../lib/engine'
import seed from './data/seed.json'

const DAY_MS = 86_400_000
const STORAGE_KEY = 'sat_studypath_demo_v1'

export interface DemoTopic {
  id: number
  section: Section
  domain: string
  skill_name: string
  frequency_weight: number
}

export interface DemoResource {
  id: number
  topic_id: number
  title: string
  url: string
  type: 'video' | 'article'
}

export interface DemoAttempt {
  topic_id: number
  correct: boolean
  difficulty: Difficulty
  at: number // epoch ms
}

export interface DemoMastery {
  mastery_score: number
  attempts_count: number
  last_practiced: number | null
}

interface SeedAttempt {
  topic_id: number
  correct: boolean
  difficulty: Difficulty
  days_ago: number
}

export const topics = seed.topics as DemoTopic[]
export const resources = seed.resources as DemoResource[]

// Seed attempts are anchored to "now" via days_ago, so the history always looks
// like the last few weeks no matter when the demo is opened.
function seededAttempts(now: number): DemoAttempt[] {
  return (seed.attempts as SeedAttempt[]).map((a) => ({
    topic_id: a.topic_id,
    correct: a.correct,
    difficulty: a.difficulty,
    at: now - a.days_ago * DAY_MS,
  }))
}

function loadExtra(): DemoAttempt[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as DemoAttempt[]
  } catch {
    /* storage unavailable */
  }
  return []
}

let extra = loadExtra()

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(extra))
  } catch {
    /* storage unavailable */
  }
}

export function allAttempts(now: number): DemoAttempt[] {
  return [...seededAttempts(now), ...extra].sort((a, b) => a.at - b.at)
}

export function masteryByTopic(now: number): Map<number, DemoMastery> {
  const byTopic = new Map<number, DemoMastery>()
  for (const attempt of allAttempts(now)) {
    let row = byTopic.get(attempt.topic_id)
    if (!row) {
      row = { mastery_score: COLD_START_MASTERY, attempts_count: 0, last_practiced: null }
      byTopic.set(attempt.topic_id, row)
    }
    row.mastery_score = updateMastery(row.mastery_score, attempt.correct)
    row.attempts_count += 1
    if (row.last_practiced === null || attempt.at > row.last_practiced) {
      row.last_practiced = attempt.at
    }
  }
  return byTopic
}

export function addAttempt(
  topicId: number,
  correct: boolean,
  difficulty: Difficulty,
): DemoAttempt {
  const attempt: DemoAttempt = { topic_id: topicId, correct, difficulty, at: Date.now() }
  extra = [...extra, attempt]
  persist()
  return attempt
}

export function extraCount(): number {
  return extra.length
}

export function resetDemo() {
  extra = []
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* storage unavailable */
  }
}
