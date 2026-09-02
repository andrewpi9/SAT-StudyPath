import { api } from './client'

export interface ProgressPoint {
  day: string
  overall_readiness: number
  math_readiness: number
  reading_writing_readiness: number
}

export interface Progress {
  range_days: number
  points: ProgressPoint[]
}

export function getProgress(days = 30): Promise<Progress> {
  return api.get<Progress>(`/progress?days=${days}`)
}
