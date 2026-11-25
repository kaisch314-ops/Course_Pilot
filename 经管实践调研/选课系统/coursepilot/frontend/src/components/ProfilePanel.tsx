import type { Requirement, Schedule, StudentProfile } from '../types'

const GOALS = ['保研', '出国', '就业', '纯兴趣']
const MODULES = ['必修', '专业选修', '通识']

interface Props {
  profile: StudentProfile
  college: string
  tags: string[]
  requirements: Requirement[]
  graduation: Record<string, number>
  earned: Record<string, number>
  current: Schedule | null
  loading: boolean
  onChange: (next: StudentProfile) => void
  onSolve: () => void
}

function Slider({
  label,
  left,
  right,
  value,
  onChange,
}: {
  label: string
  left: string
  right: string
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="slider">
      <div className="slider-head">
        <span>{label}</span>
        <b>{Math.round(value * 100)}</b>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={Math.round(value * 100)}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
      />
      <div className="slider-ends">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  )
}

export default function ProfilePanel({
  profile,
  college,
  tags,
  requirements,
  graduation,
  earned,
  current,
  loading,
  onChange,
  onSolve,
}: Props) {
  const patch = (p: Partial<StudentProfile>) => onChange({ ...profile, ...p })
  const toggleTag = (t: string) => {
    const has = profile.interests.includes(t)
    patch({ interests: has ? profile.interests.filter((x) => x !== t) : [...profile.interests, t] })
  }

  return (
    <aside className="panel">
      <div className="panel-block">
        <div className="panel-label">学生档案</div>
        <div className="panel-name">
          {profile.grade} 级 · {profile.major}
        </div>
        <div className="panel-meta">
          {college} · 已修 {profile.completed.length} 门
        </div>
      </div>

      <div className="panel-block">
        <div className="panel-label">毕业学分进度</div>
        <div className="progress-list">
          {MODULES.map((m) => {
            const total = graduation[m] ?? 0
            const done = earned[m] ?? 0
            const now = current
              ? current.items.filter((i) => i.category === m).reduce((a, b) => a + b.credits, 0)
              : 0
            const donePct = total ? Math.min(100, (done / total) * 100) : 0
            const nowPct = total ? Math.min(100 - donePct, (now / total) * 100) : 0
            return (
              <div key={m} className="progress-row">
                <div className="progress-head">
                  <span>{m}</span>
                  <span className="progress-num">
                    {done}
                    <i>+{now}</i> / {total}
                  </span>
                </div>
                <div className="progress-track">
                  <div className="progress-done" style={{ width: `${donePct}%` }} />
                  <div className="progress-now" style={{ width: `${nowPct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="panel-block">
        <div className="panel-label">目标</div>
        <div className="seg">
          {GOALS.map((g) => (
            <button
              key={g}
              className={profile.goal === g ? 'on' : ''}
              onClick={() => patch({ goal: g })}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="panel-block">
        <div className="panel-label">三个滑杆决定权重</div>
        <Slider
          label="课程取向"
          left="分数优先"
          right="学到东西"
          value={profile.focus}
          onChange={(v) => patch({ focus: v })}
        />
        <Slider
          label="强度偏好"
          left="轻松"
          right="挑战"
          value={profile.challenge}
          onChange={(v) => patch({ challenge: v })}
        />
        <Slider
          label="风险偏好"
          left="稳妥"
          right="探索"
          value={profile.exploration}
          onChange={(v) => patch({ exploration: v })}
        />
      </div>

      <div className="panel-block">
        <div className="panel-label">感兴趣的标签</div>
        <div className="chips">
          {tags.map((t) => (
            <button
              key={t}
              className={`chip ${profile.interests.includes(t) ? 'on' : ''}`}
              onClick={() => toggleTag(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="panel-block">
        <div className="panel-label">作息与学分</div>
        <label className="check">
          <input
            type="checkbox"
            checked={profile.avoid_early}
            onChange={(e) => patch({ avoid_early: e.target.checked })}
          />
          尽量避开早八
        </label>
        <div className="credit-row">
          <label>
            最低
            <input
              type="number"
              min={0}
              max={40}
              value={profile.min_credits}
              onChange={(e) => patch({ min_credits: Number(e.target.value) })}
            />
          </label>
          <label>
            最高
            <input
              type="number"
              min={0}
              max={40}
              value={profile.max_credits}
              onChange={(e) => patch({ max_credits: Number(e.target.value) })}
            />
          </label>
        </div>
        <div className="req-hint">
          培养要求：{requirements.map((r) => `${r.module} ≥ ${r.min_credits}`).join(' · ')}
        </div>
      </div>

      <button className="solve-btn" onClick={onSolve} disabled={loading}>
        {loading ? '求解中…' : '生成课表方案'}
      </button>
    </aside>
  )
}
