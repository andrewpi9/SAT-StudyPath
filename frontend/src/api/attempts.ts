import { api } from './client'
import type { AttemptResult, Difficulty } from './types'

export interface LogAttemptPayload {
  topic_id: number
  correct: boolean
  time_taken_seconds: number
  difficulty: Difficulty
}

export function logAttempt(payload: LogAttemptPayload): Promise<AttemptResult> {
  return api.post<AttemptResult>('/attempts', payload)
}
