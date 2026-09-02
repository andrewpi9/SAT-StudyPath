import { masteryBand } from '../lib/masteryBand'

const round = (n: number) => Math.round(n * 100)

/** A compact mastery indicator: a coloured bar + the percentage. */
export default function MasteryBar({
  mastery,
  attempts,
  width = 'w-24',
}: {
  mastery: number
  attempts: number
  width?: string
}) {
  if (attempts === 0) {
    return <span className="text-xs text-slate-400">not practiced yet</span>
  }

  const band = masteryBand(mastery, attempts)
  return (
    <span className="flex items-center gap-2">
      <span className={`h-1.5 overflow-hidden rounded-full bg-slate-100 ${width}`}>
        <span
          className="block h-full rounded-full"
          style={{ width: `${round(mastery)}%`, backgroundColor: band.bg }}
        />
      </span>
      <span className="text-xs font-medium tabular-nums text-slate-600">{round(mastery)}%</span>
    </span>
  )
}
