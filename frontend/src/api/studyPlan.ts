import { api } from './client'
import type { StudyPlan } from './types'

export function getStudyPlan(limit = 5): Promise<StudyPlan> {
  return api.get<StudyPlan>(`/study-plan?limit=${limit}`)
}
