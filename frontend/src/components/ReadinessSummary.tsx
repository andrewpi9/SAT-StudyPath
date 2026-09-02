import type { MasteryOverview } from '../api/types'

const pct = (n: number) => `${Math.round(n * 100)}%`

function Tile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-slate-200 px-4 py-3">
      <div className="text-2xl font-bold tabular-nums text-slate-900">{pct(value)}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}

export default function ReadinessSummary({ data }: { data: MasteryOverview }) {
  return (
    <div className="flex flex-wrap gap-3">
      <Tile label="Overall readiness" value={data.overall_readiness} />
      <Tile label="Math" value={data.section_readiness.Math} />
      <Tile label="Reading & Writing" value={data.section_readiness.ReadingWriting} />
    </div>
  )
}
