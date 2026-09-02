import { api } from './client'
import type { MasteryOverview } from './types'

export function getMastery(): Promise<MasteryOverview> {
  return api.get<MasteryOverview>('/mastery')
}
