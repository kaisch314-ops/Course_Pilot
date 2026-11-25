import { useState } from 'react'
import type { Offering, ScheduleItem, Session } from '../types'
import { CATEGORY_COLOR } from './Timetable'

function overlaps(a: Session[], b: Session[]) {
  return a.some((x) =>
    b.some((y) => x.day === y.day && !(x.end < y.start || y.end < x.start)),
  )
}

interface Props {
  item: ScheduleItem
  offerings: Offering[]
  siblings: ScheduleItem[]
  busy: boolean
  onSwap: (item: ScheduleItem, replacementId: string) => void
}

export default function CourseCard({ item, offerings, siblings, busy, onSwap }: Props) {
  const [open, setOpen] = useState(false)

  const parts = Object.entries(item.contributions).sort((a, b) => b[1] - a[1])
  const max = Math.max(...parts.map((p) => p[1]), 1)
  const color = CATEGORY_COLOR[item.category] ?? 'var(--major)'

  const alternatives = offerings.filter(
    (o) => o.code === item.code && o.id !== item.offering_id,
  )
  const others = siblings.filter((s) => s.offering_id !== item.offering_id)

  const conflictOf = (alt: Offering) => {
    const withTime = others.find((s) => overlaps(alt.sessions, s.sessions))
    return withTime ? `与「${withTime.name}」冲突` : ''
  }

  return (
    <div className="card">
      <div className="card-top">
        <div>
          <div className="card-title">
            <span className="pip" style={{ background: color }} />
            {item.name}
            <span className="code">{item.code}</span>
          </div>
          <div className="card-sub">
            {item.teacher} · {item.credits} 学分 · {item.style}
          </div>
        </div>
        <div className="score-ring">
          <b>{Math.round(item.score)}</b>
          <span>效用</span>
        </div>
      </div>

      <p className="card-summary">{item.summary}</p>

      <div className="metrics">
        <div>
          <span className="m-label">周投入</span>
          <span className="m-value">{item.weekly_hours}h</span>
        </div>
        <div>
          <span className="m-label">难度</span>
          <span className="m-value">{item.difficulty.toFixed(1)}</span>
        </div>
        <div>
          <span className="m-label">给分</span>
          <span className="m-value">{item.grading.toFixed(1)}</span>
        </div>
        <div>
          <span className="m-label">教师</span>
          <span className="m-value">{item.teacher_rating.toFixed(1)}</span>
        </div>
        <div>
          <span className="m-label">历史中签</span>
          <span className={`m-value ${item.admit_rate < 0.35 ? 'risk' : ''}`}>
            {Math.round(item.admit_rate * 100)}%
          </span>
        </div>
      </div>

      <div className="bars">
        {parts.map(([k, v]) => (
          <div key={k} className="bar-row">
            <span className="bar-label">{k}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(v / max) * 100}%` }} />
            </div>
            <span className="bar-num">{v.toFixed(1)}</span>
          </div>
        ))}
      </div>

      <div className="tags">
        {item.tags.map((t) => (
          <span key={t} className="tag">
            {t}
          </span>
        ))}
      </div>

      {alternatives.length > 0 && (
        <div className="swap">
          <button className="swap-toggle" onClick={() => setOpen((v) => !v)}>
            {open ? '收起班次' : `换班次 · ${alternatives.length} 个可选`}
          </button>
          {open && (
            <div className="alts">
              {alternatives.map((alt) => {
                const conflict = conflictOf(alt)
                return (
                  <div key={alt.id} className={`alt ${conflict ? 'off' : ''}`}>
                    <div className="alt-main">
                      <b>{alt.teacher}</b>
                      <span>评分 {alt.teacher_rating.toFixed(1)}</span>
                      <span>中签 {Math.round(alt.admit_rate * 100)}%</span>
                      <span className="alt-time">
                        {alt.sessions
                          .map((s) => `${['一', '二', '三', '四', '五'][s.day - 1]} ${s.start}-${s.end}`)
                          .join(' / ')}
                      </span>
                    </div>
                    {conflict ? (
                      <span className="alt-block">{conflict}</span>
                    ) : (
                      <button
                        className="alt-btn"
                        disabled={busy}
                        onClick={() => onSwap(item, alt.id)}
                      >
                        换到这门
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
