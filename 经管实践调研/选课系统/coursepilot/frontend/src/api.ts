import type {
  Bootstrap,
  CourseIntro,
  Identity,
  QAItem,
  SolveResponse,
  StudentProfile,
  SwapResponse,
  TeacherMe,
  TeacherSummary,
} from './types'

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

export const getBootstrap = () => json<Bootstrap>('/api/bootstrap')

export const solve = (profile: StudentProfile) =>
  json<SolveResponse>('/api/solve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  })

export const swap = (body: {
  offering_ids: string[]
  target: string
  replacement: string
  profile: StudentProfile
}) =>
  json<SwapResponse>('/api/swap', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const getMe = () => json<Identity>('/api/auth/me')

// ---- 教师端 ----
export const getTeacherMe = () => json<TeacherMe>('/api/teacher/me')

export const getTeacherSummary = (course: string) =>
  json<TeacherSummary>(`/api/teacher/summary?course=${encodeURIComponent(course)}`)

export const refreshTeacherSummary = (course: string) =>
  json<TeacherSummary>(`/api/teacher/summary/refresh?course=${encodeURIComponent(course)}`, { method: 'POST' })

export const getTeacherIntro = (course: string) =>
  json<CourseIntro>(`/api/teacher/intro?course=${encodeURIComponent(course)}`)

export const putTeacherIntro = (intro: CourseIntro) =>
  json<{ saved: boolean }>('/api/teacher/intro', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(intro),
  })

export const getTeacherQA = () => json<QAItem[]>('/api/teacher/qa')

export const answerQuestion = (id: string, text: string) =>
  json<{ answered: boolean }>(`/api/teacher/qa/${encodeURIComponent(id)}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })

// ---- 学生端可见的简介与问答 ----
export const getCourseIntro = (course: string) =>
  json<{ course: string; teachers: string[]; intros: CourseIntro[] }>(
    `/api/intro?course=${encodeURIComponent(course)}`,
  )

export const getCourseQA = (course: string) => json<QAItem[]>(`/api/qa?course=${encodeURIComponent(course)}`)

export const askQuestion = (body: { course_code: string; teacher: string; text: string }) =>
  json<{ asked: boolean }>('/api/qa', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
