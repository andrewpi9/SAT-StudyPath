import { useMemo, useState } from 'react'

import type { ProgressPoint } from '../api/progress'
import Card from './Card'

const W = 680
const H = 180
const PAD = { top: 16, right: 16, bottom: 24, left: 34 }
const INNER_W = W - PAD.left - PAD.right
const INNER_H = H - PAD.top - PAD.bottom

const fmtPct = (n: number) => `${Math.round(n * 100)}%`
const fmtDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export default function ReadinessTrend({ points }: { points: ProgressPoint[] }) {
  const [hover, setHover] = useState<number | null>(null)

  const geom = useMemo(() => {
    const values = points.map((p) => p.overall_readiness)
    const lo = Math.max(0, Math.min(...values) - 0.05)
    const hi = Math.min(1, Math.max(...values) + 0.05)
    const span = hi - lo || 1

    const x = (i: number) =>
      PAD.left + (points.length === 1 ? INNER_W / 2 : (i / (points.length - 1)) * INNER_W)
    const y = (v: number) => PAD.top + (1 - (v - lo) / span) * INNER_H

    const line = points.map((p, i) => `${x(i)},${y(p.overall_readiness)}`).join(' ')
    const area = `${PAD.left},${PAD.top + INNER_H} ${line} ${PAD.left + INNER_W},${PAD.top + INNER_H}`
    return { x, y, line, area, lo, hi }
  }, [points])

  if (points.length < 2) return null

  const last = points[points.length - 1]
  const active = hover === null ? null : points[hover]

  function onMove(event: React.MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect()
    const px = ((event.clientX - rect.left) / rect.width) * W
    const ratio = (px - PAD.left) / INNER_W
    const i = Math.round(ratio * (points.length - 1))
    setHover(Math.min(points.length - 1, Math.max(0, i)))
  }

  return (
    <Card className="p-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Readiness — last {points.length} days
        </h2>
        <span className="text-xs text-slate-400 dark:text-slate-500">
          {fmtPct(points[0].overall_readiness)} → {fmtPct(last.overall_readiness)}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-2 w-full"
        role="img"
        aria-label={`Overall readiness rose from ${fmtPct(points[0].overall_readiness)} to ${fmtPct(last.overall_readiness)} over ${points.length} days`}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {[geom.hi, (geom.hi + geom.lo) / 2, geom.lo].map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              x2={PAD.left + INNER_W}
              y1={geom.y(v)}
              y2={geom.y(v)}
              className="stroke-slate-200 dark:stroke-slate-800"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 6}
              y={geom.y(v) + 3}
              textAnchor="end"
              fontSize={10}
              className="fill-slate-400 dark:fill-slate-500"
            >
              {fmtPct(v)}
            </text>
          </g>
        ))}

        <polygon points={geom.area} className="fill-indigo-500" fillOpacity={0.12} />
        <polyline points={geom.line} fill="none" className="stroke-indigo-500" strokeWidth={2} />

        <circle
          cx={geom.x(points.length - 1)}
          cy={geom.y(last.overall_readiness)}
          r={3}
          className="fill-indigo-500"
        />

        <text
          x={PAD.left}
          y={H - 6}
          fontSize={10}
          className="fill-slate-400 dark:fill-slate-500"
        >
          {fmtDay(points[0].day)}
        </text>
        <text
          x={PAD.left + INNER_W}
          y={H - 6}
          textAnchor="end"
          fontSize={10}
          className="fill-slate-400 dark:fill-slate-500"
        >
          {fmtDay(last.day)}
        </text>

        {active && hover !== null && (
          <g>
            <line
              x1={geom.x(hover)}
              x2={geom.x(hover)}
              y1={PAD.top}
              y2={PAD.top + INNER_H}
              className="stroke-slate-300 dark:stroke-slate-600"
              strokeWidth={1}
            />
            <circle
              cx={geom.x(hover)}
              cy={geom.y(active.overall_readiness)}
              r={3.5}
              className="fill-indigo-500 stroke-white dark:stroke-slate-900"
              strokeWidth={1.5}
            />
            <text
              x={Math.min(geom.x(hover) + 6, PAD.left + INNER_W)}
              y={PAD.top + 10}
              textAnchor={geom.x(hover) > PAD.left + INNER_W - 80 ? 'end' : 'start'}
              fontSize={11}
              className="fill-slate-900 dark:fill-slate-100"
            >
              {fmtDay(active.day)} · {fmtPct(active.overall_readiness)}
            </text>
          </g>
        )}
      </svg>
    </Card>
  )
}
