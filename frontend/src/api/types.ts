/** Mirrors the Pydantic response models in backend/app/schemas/. */

export type Section = 'Math' | 'ReadingWriting'
export type Difficulty = 'easy' | 'medium' | 'hard'

export interface Topic {
  id: number
  section: Section
  domain: string
  skill_name: string
  frequency_weight: number
}

export interface TopicMastery {
  topic_id: number
  skill_name: string
  section: Section
  domain: string
  frequency_weight: number
  mastery_score: number
  decayed_mastery: number
  confidence: number
  attempts_count: number
  last_practiced: string | null
  days_since_practice: number | null
}

export interface MasteryOverview {
  generated_at: string
  overall_readiness: number
  section_readiness: Record<Section, number>
  topics: TopicMastery[]
}

export interface StudyPlanItem extends TopicMastery {
  urgency: number
  exploration_bonus: number
  priority_score: number
  reason: string
}

export interface StudyPlan {
  generated_at: string
  limit: number
  items: StudyPlanItem[]
}

export interface AttemptResult {
  attempt: {
    id: number
    topic_id: number
    correct: boolean
    time_taken_seconds: number
    difficulty: Difficulty
    timestamp: string
  }
  mastery: TopicMastery
}

export const SECTION_LABEL: Record<Section, string> = {
  Math: 'Math',
  ReadingWriting: 'Reading & Writing',
}
