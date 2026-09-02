import * as demoApi from '../demo/api'
import { DEMO } from '../lib/demo'
import { api } from './client'
import type { MasteryOverview } from './types'

export function getMastery(): Promise<MasteryOverview> {
  return DEMO ? demoApi.getMastery() : api.get<MasteryOverview>('/mastery')
}
