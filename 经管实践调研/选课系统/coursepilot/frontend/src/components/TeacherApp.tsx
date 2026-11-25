import { useCallback, useEffect, useState } from 'react'
import {
  answerQuestion,
  getTeacherIntro,
  getTeacherMe,
  getTeacherQA,
  getTeacherSummary,
  putTeacherIntro,
  refreshTeacherSummary,
} from '../api'
import type { CourseIntro, QAItem, TeacherMe, TeacherSummary } from '../types'

const KIND_LABEL: Record<string, string> = {
  reviews: '选课社区评价总结',
  preferences: '学生偏好的上课模式',
  advice: '推荐的改进方式',
}

function SummaryPanel({ code }: { code: string }) {
  const [data, setData] = useState<TeacherSummary>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = useCallback(async (refresh: boolean) => {
    setBusy(true)
    setError('')
    try {
      setData(refresh ? await refreshTeacherSummary(code) : await getTeacherSummary(code))
    } catch (e) {
      setError(e instanceof Error ? e.message : '总结生成失败')
    } finally {
      setBusy(false)
    }
  }, [code])
  useEffect(() => {
    void load(false)
  }, [load])
  return (
    <details open>
      <summary>AI 教学反馈总结</summary>
      {busy && <p role="status">正在生成总结…</p>}
      {error && <p role="alert">{error}</p>}
      {(['reviews', 'preferences', 'advice'] as const).map((k) => {
        const block = data?.kinds[k]
        if (!block) return null
        return (
          <section key={k}>
            <h4>{KIND_LABEL[k]}</h4>
            <p style={{ whiteSpace: 'pre-wrap' }}>{block.content}</p>
            <small>
              来源：{block.source === 'llm' ? '大模型生成' : '本地规则生成'} ·{' '}
              {new Date(block.generated_at).toLocaleString()} · 演示数据
            </small>
          </section>
        )
      })}
      <button disabled={busy} onClick={() => void load(true)}>
        重新生成
      </button>
    </details>
  )
}

function IntroEditor({ code, teacher }: { code: string; teacher: string }) {
  const [intro, setIntro] = useState<CourseIntro>({
    teacher,
    course_code: code,
    style: '',
    attendance: '',
    assessment: '',
    expectation: '',
  })
  const [status, setStatus] = useState('')
  useEffect(() => {
    getTeacherIntro(code)
      .then((i) => setIntro((prev) => ({ ...prev, ...i })))
      .catch(() => setStatus('简介读取失败'))
  }, [code])
  async function save() {
    setStatus('保存中…')
    try {
      await putTeacherIntro(intro)
      setStatus('已保存，学生端同步可见。')
    } catch (e) {
      setStatus(e instanceof Error ? e.message : '保存失败')
    }
  }
  const field = (key: keyof CourseIntro, label: string, hint: string) => (
    <label>
      {label}
      <textarea
        value={String(intro[key] ?? '')}
        placeholder={hint}
        onChange={(e) => setIntro({ ...intro, [key]: e.target.value })}
      />
    </label>
  )
  return (
    <details open>
      <summary>课程简介（同步到学生端）</summary>
      {field('style', '教学方式', '例如：案例驱动，课堂大量讨论')}
      {field('attendance', '点名方式', '例如：随机点名，约占 1/3 课时')}
      {field('assessment', '考核方式', '例如：平时作业 40% + 期末 60%')}
      {field('expectation', '希望学生是什么样的', '例如：敢开口发言，或认真完成作业')}
      <button className="primary" onClick={() => void save()}>
        保存简介
      </button>
      {status && <p role="status">{status}</p>}
    </details>
  )
}

function QAList({ items, onAnswered }: { items: QAItem[]; onAnswered: () => void }) {
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState('')
  async function answer(id: string) {
    setBusy(id)
    try {
      await answerQuestion(id, drafts[id] || '')
      setDrafts((d) => ({ ...d, [id]: '' }))
      onAnswered()
    } finally {
      setBusy('')
    }
  }
  const unanswered = items.filter((q) => !q.answer)
  const answered = items.filter((q) => q.answer)
  return (
    <details open>
      <summary>
        学生提问（未回复 {unanswered.length} / 共 {items.length}）
      </summary>
      {items.length === 0 && <p>暂无学生提问。</p>}
      {[...unanswered, ...answered].map((q) => (
        <section key={q.id}>
          <p>
            <b>{q.student_name}</b>（{q.course_code}）：{q.text}
          </p>
          <small>{new Date(q.time).toLocaleString()}</small>
          {q.answer && (
            <p>
              已回复：{q.answer} <small>{q.answer_time && new Date(q.answer_time).toLocaleString()}</small>
            </p>
          )}
          <label>
            {q.answer ? '修改回复' : '回复该同学'}
            <textarea
              value={drafts[q.id] ?? q.answer ?? ''}
              onChange={(e) => setDrafts({ ...drafts, [q.id]: e.target.value })}
            />
          </label>
          <button
            className="primary"
            disabled={busy === q.id || !(drafts[q.id] ?? q.answer ?? '').trim()}
            onClick={() => void answer(q.id)}
          >
            {busy === q.id ? '提交中…' : q.answer ? '更新回复' : '回复'}
          </button>
        </section>
      ))}
    </details>
  )
}

export default function TeacherApp() {
  const [me, setMe] = useState<TeacherMe>()
  const [qa, setQA] = useState<QAItem[]>([])
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const loadQA = useCallback(() => {
    getTeacherQA()
      .then(setQA)
      .catch(() => setError('提问列表读取失败'))
  }, [])
  useEffect(() => {
    getTeacherMe()
      .then((m) => {
        setMe(m)
        setSelected(m.courses[0]?.code || '')
      })
      .catch(() => setError('教师信息读取失败，请确认以教师身份登录'))
    loadQA()
  }, [loadQA])
  if (error) return <p role="alert">{error}</p>
  if (!me) return <p>正在读取教师工作台…</p>
  const course = me.courses.find((c) => c.code === selected)
  const pendingCount = (code: string) => qa.filter((q) => q.course_code === code && !q.answer).length
  return (
    <div className="desk">
      <nav className="mast">
        <strong>
          <i aria-hidden="true">▦</i> CoursePilot 教师端
        </strong>
        <div>
          <a href="#courses">我的课程</a>
        </div>
      </nav>
      <header className="cover">
        <div>
          <small>上海交通大学　/　教师工作台</small>
          <h1>{me.teacher_name} 老师，您好</h1>
        </div>
        <p>
          本学期 {me.courses.length} 门课 <span>演示数据</span>
        </p>
      </header>
      <div className="workspace" id="courses">
        <aside>
          <b>我的课程</b>
          {me.courses.map((c) => (
            <button
              key={c.code}
              aria-pressed={selected === c.code}
              style={{ display: 'block', width: '100%', textAlign: 'left' }}
              onClick={() => setSelected(c.code)}
            >
              {c.name}
              <br />
              <small>
                {c.code}
                {pendingCount(c.code) > 0 && ` · ${pendingCount(c.code)} 条待回复`}
              </small>
            </button>
          ))}
        </aside>
        <main>
          {course && (
            <article key={course.code}>
              <h3>
                {course.name} <small>{course.code}</small>
              </h3>
              <p>
                {course.offerings.map((o) => `${o.id} · ${o.enrolled}/${o.capacity} 人`).join('　')}
              </p>
              <SummaryPanel code={course.code} />
              <IntroEditor code={course.code} teacher={me.teacher_name} />
              <QAList items={qa.filter((q) => q.course_code === course.code)} onAnswered={loadQA} />
            </article>
          )}
        </main>
      </div>
    </div>
  )
}
