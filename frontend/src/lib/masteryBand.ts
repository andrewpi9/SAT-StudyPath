/**
 * Mastery -> colour band for the heatmap.
 *
 * Colours are the data-viz *status* palette (fixed, never themed): a skill's
 * band is a state ("needs work" ... "solid"), not a series identity. The band is
 * always shown with its percentage and a text label too, so colour never
 * carries the meaning alone.
 */

export type BandKey = 'untouched' | 'critical' | 'serious' | 'warning' | 'good'

export interface Band {
  key: BandKey
  label: string
  bg: string
  fg: string
}

export const BANDS: Record<BandKey, Band> = {
  untouched: { key: 'untouched', label: 'Not started', bg: '#eceae4', fg: '#5c5b57' },
  critical: { key: 'critical', label: 'Needs work', bg: '#d03b3b', fg: '#ffffff' },
  serious: { key: 'serious', label: 'Shaky', bg: '#ec835a', fg: '#1a1a19' },
  warning: { key: 'warning', label: 'Getting there', bg: '#fab219', fg: '#1a1a19' },
  good: { key: 'good', label: 'Solid', bg: '#0ca30c', fg: '#ffffff' },
}

/** Ordered weak -> strong, for legends. */
export const BAND_ORDER: BandKey[] = ['critical', 'serious', 'warning', 'good', 'untouched']

export function masteryBand(decayedMastery: number, attemptsCount: number): Band {
  if (attemptsCount === 0) return BANDS.untouched
  if (decayedMastery < 0.3) return BANDS.critical
  if (decayedMastery < 0.5) return BANDS.serious
  if (decayedMastery < 0.7) return BANDS.warning
  return BANDS.good
}
