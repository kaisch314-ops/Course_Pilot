import { useCallback, useEffect, useState } from 'react'
import { askQuestion, getCourseIntro, getCourseQA } from '../api'
import type { CourseIntro, QAItem } from '../types'

export function TeacherIntro({ code }: { code: string }) {
  const [data, setData] = useState<{ teachers: string[]; intros: CourseIntro[] }>()
  const [error, setError] = useState('')
  useEffect(() => {
    getCourseIntro(code)
      .then((d) => setData({ teachers: d.teachers, intros: d.intros }))
      .catch(() => setError('教师简介读取失败'))
  }, [code])
  return (
    <details>
      <summary>教师简介与教学说明</summary>
      {error && <p role="alert">{error}</p>}
      {data && data.intros.length === 0 && <p>授课教师还未填写简介，可在下方提问。</p>}
      {data?.intros.map((i) => (
        <section key={i.teacher}>
          <h4>{i.teacher} 老师</h4>
          {i.style && (
            <p>
              <b>教学方式：</b>
              {i.style}
            </p>
          )}
          {i.attendance && (
            <p>
              <b>点名方式：</b>
              {i.attendance}
            </p>
          )}
          {i.assessment && (
            <p>
              <b>考核方式：</b>
              {i.assessment}
            </p>
          )}
          {i.expectation && (
            <p>
              <b>期望的学生：</b>
              {i.expectation}
            </p>
          )}
          {i.updated_at && <small>更新于 {new Date(i.updated_at).toLocaleString()}</small>}
        </section>
      ))}
    </details>
  )
}

export function QABoard({ code, teachers }: { code: string; teachers: string[] }) {
  const [items, setItems] = useState<QAItem[]>()
  const [text, setText] = useState('')
  const [teacher, setTeacher] = useState(teachers[0] || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = useCallback(() => {
    getCourseQA(code)
      .then(setItems)
      .catch(() => setError('提问区读取失败'))
  }, [code])
  useEffect(load, [load])
  async function ask() {
    setBusy(true)
    setError('')
    try {
      await askQuestion({ course_code: code, teacher, text: text.trim() })
      setText('')
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : '提交失败')
    } finally {
      setBusy(false)
    }
  }
  return (
    <details>
      <summary>向老师提问（{items?.length ?? 0} 条）</summary>
      {error && <p role="alert">{error}</p>}
      {items?.map((q) => (
        <section key={q.id}>
          <p>
            <b>{q.student_name}</b> 问 {q.teacher} 老师：{q.text}
          </p>
          <small>{new Date(q.time).toLocaleString()}</small>
          {q.answer ? (
            <p>
              <b>{q.teacher} 回复：</b>
              {q.answer}
            </p>
          ) : (
            <p>
              <small>老师还未回复，回复后所有同学可见。</small>
            </p>
          )}
        </section>
      ))}
      <label>
        提问对象
        <select value={teacher} onChange={(e) => setTeacher(e.target.value)}>
          {teachers.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      <label>
        你的问题（所有选这门课的同学都能看到）
        <textarea
          value={text}
          minLength={2}
          maxLength={1000}
          placeholder="例如：期末考核是开卷还是闭卷？"
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <button className="primary" disabled={busy || text.trim().length < 2 || !teacher} onClick={() => void ask()}>
        {busy ? '提交中…' : '提交提问'}
      </button>
    </details>
  )
}
