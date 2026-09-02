import type { MasteryOverview } from '../api/types'
import { masteryBand } from '../lib/masteryBand'
import Card from './Card'

const pct = (n: number) => `${Math.round(n * 100)}%`

function Tile({ label, value }: { label: string; value: number }) {
  const band = masteryBand(value, 1)
  return (
    <Card className="flex-1 p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1 text-3xl font-bold tabular-nums text-slate-900">{pct(value)}</div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full"
          style={{ width: pct(value), backgroundColor: band.bg }}
        />
      </div>
    </Card>
  )
}

export default function ReadinessSummary({ data }: { data: MasteryOverview }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Tile label="Overall readiness" value={data.overall_readiness} />
      <Tile label="Math" value={data.section_readiness.Math} />
      <Tile label="Reading & Writing" value={data.section_readiness.ReadingWriting} />
    </div>
  )
}
