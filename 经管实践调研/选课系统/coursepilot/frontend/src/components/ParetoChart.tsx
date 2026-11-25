import type { FrontierPoint, Schedule } from '../types'

interface Props {
  points: FrontierPoint[]
  highlights: Schedule[]
  selected: number
}

const W = 680
const H = 300
const PAD = { l: 48, r: 20, t: 18, b: 42 }

export default function ParetoChart({ points, highlights, selected }: Props) {
  if (!points.length) return null

  const xs = points.map((p) => p.hours)
  const ys = points.map((p) => p.expected)
  const xMin = Math.min(...xs) - 3
  const xMax = Math.max(...xs) + 3
  const yMax = Math.max(...ys) + 1.5
  const innerW = W - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b

  const sx = (v: number) => PAD.l + ((v - xMin) / (xMax - xMin || 1)) * innerW
  const sy = (v: number) => H - PAD.b - (v / (yMax || 1)) * innerH

  const xTicks = Array.from({ length: 5 }, (_, i) => xMin + ((xMax - xMin) / 4) * i)
  const yTicks = Array.from({ length: 4 }, (_, i) => (yMax / 3) * i)

  // 非支配边界：按周投入排序后，期望学分严格递增的点
  const sorted = [...points].sort((a, b) => a.hours - b.hours)
  const hull: FrontierPoint[] = []
  for (const p of sorted) {
    if (!hull.length || p.expected > hull[hull.length - 1].expected) hull.push(p)
  }

  const hullPath = hull
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.hours).toFixed(1)},${sy(p.expected).toFixed(1)}`)
    .join(' ')

  const nearest = (s: Schedule) => {
    let best = points[0]
    let bestD = Infinity
    for (const p of points) {
      const d = Math.abs(p.hours - s.total_weekly_hours) + Math.abs(p.expected - s.expected_credits) * 3
      if (d < bestD) {
        bestD = d
        best = p
      }
    }
    return best
  }

  return (
    <figure className="chart">
      <figcaption>
        权衡图：每个点是一套可行课表，横轴为周课外投入，纵轴为按中签率折算的期望学分
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="课表权衡散点图">
        {yTicks.map((t) => (
          <g key={`y${t}`}>
            <line x1={PAD.l} x2={W - PAD.r} y1={sy(t)} y2={sy(t)} className="grid-line" />
            <text x={PAD.l - 8} y={sy(t) + 3.5} className="axis-text" textAnchor="end">
              {t.toFixed(1)}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <g key={`x${t}`}>
            <line x1={sx(t)} x2={sx(t)} y1={PAD.t} y2={H - PAD.b} className="grid-line" />
            <text x={sx(t)} y={H - PAD.b + 16} className="axis-text" textAnchor="middle">
              {Math.round(t)}h
            </text>
          </g>
        ))}

        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} className="axis-line" />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={H - PAD.b} className="axis-line" />

        <path d={hullPath} className="hull-line" />

        {points.map((p, i) => (
          <circle
            key={i}
            cx={sx(p.hours)}
            cy={sy(p.expected)}
            r={3}
            className="dot-normal"
          />
        ))}

        {highlights.map((s, i) => {
          const p = nearest(s)
          return (
            <g key={s.id}>
              <circle
                cx={sx(p.hours)}
                cy={sy(p.expected)}
                r={i === selected ? 7 : 5}
                className={i === selected ? 'dot-active' : 'dot-pick'}
              />
              <text
                x={sx(p.hours)}
                y={sy(p.expected) - 12}
                className="dot-label"
                textAnchor="middle"
              >
                方案 {i + 1}
              </text>
            </g>
          )
        })}

        <text x={W - PAD.r} y={H - 8} className="axis-title" textAnchor="end">
          周课外投入 →
        </text>
        <text x={PAD.l - 34} y={PAD.t + 2} className="axis-title">
          期望学分
        </text>
      </svg>
    </figure>
  )
}
