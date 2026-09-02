import * as demoApi from '../demo/api'
import { DEMO } from '../lib/demo'
import { api } from './client'
import type { StudyPlan } from './types'

export function getStudyPlan(limit = 5): Promise<StudyPlan> {
  return DEMO ? demoApi.getStudyPlan(limit) : api.get<StudyPlan>(`/study-plan?limit=${limit}`)
}
