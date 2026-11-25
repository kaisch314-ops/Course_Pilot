export interface Session {
  weeks?: number[]
  day: number
  start: number
  end: number
  location: string
}

export interface CourseProfile {
  weekly_hours: number
  difficulty: number
  grading: number
  style: string
  attendance: boolean
  assessment: Record<string, number>
  sample_size: number
  confidence: number
  summary: string
}

export interface Course {
  code: string
  name: string
  credits: number
  category: string
  prereqs: string[]
  tags: string[]
  profile: CourseProfile
}

export interface Offering {
  id: string
  code: string
  teacher: string
  teacher_rating: number
  admit_rate: number
  capacity: number
  enrolled: number
  sessions: Session[]
}

export interface PlanItem {
  code: string
  module: string
  suggest_term: number
}

export interface Requirement {
  module: string
  min_credits: number
}

export interface StudentProfile {
  name: string
  major: string
  grade: number
  completed: string[]
  interests: string[]
  affinity?: Record<string, number>
  goal: string
  focus: number
  challenge: number
  exploration: number
  locked: string[]
  excluded: string[]
  blocked: Session[]
  avoid_early: boolean
  min_credits: number
  max_credits: number
}

export interface ScheduleItem {
  offering_id: string
  code: string
  name: string
  credits: number
  category: string
  teacher: string
  teacher_rating: number
  admit_rate: number
  sessions: Session[]
  weekly_hours: number
  difficulty: number
  grading: number
  style: string
  summary: string
  tags: string[]
  score: number
  contributions: Record<string, number>
}

export interface Schedule {
  id: string
  items: ScheduleItem[]
  total_credits: number
  expected_credits: number
  total_weekly_hours: number
  avg_difficulty: number
  used_days: number
  score: number
  headline: string
  reasons: string[]
  warnings: string[]
}

export interface FrontierPoint {
  credits: number
  hours: number
  expected: number
  difficulty: number
  score: number
}

export interface SolveResponse {
  schedules: Schedule[]
  frontier: FrontierPoint[]
  diagnostics: string[]
}

export interface SwapResponse {
  ok: boolean
  schedule: Schedule | null
  message: string
}

export interface Bootstrap {
  term: string
  major: string
  college: string
  grade: number
  notice: string
  completed: string[]
  graduation: Record<string, number>
  earned: Record<string, number>
  plan: PlanItem[]
  requirements: Requirement[]
  courses: Course[]
  offerings: Offering[]
  default_profile: StudentProfile
}

// ---- 身份与教师端 ----
export interface Identity {
  username: string
  student_id: string | null
  role: 'student' | 'teacher'
  teacher_name: string | null
}

export interface TeacherMe {
  teacher_name: string
  courses: { code: string; name: string; credits: number; offerings: Offering[] }[]
  llm_ready: boolean
}

export interface SummaryBlock {
  content: string
  source: 'rules' | 'llm'
  generated_at: string
}

export interface TeacherSummary {
  course: string
  cached: boolean
  kinds: { reviews?: SummaryBlock; preferences?: SummaryBlock; advice?: SummaryBlock }
}

export interface CourseIntro {
  teacher: string
  course_code: string
  style: string
  attendance: string
  assessment: string
  expectation: string
  updated_at?: string
}

export interface QAItem {
  id: string
  course_code?: string
  teacher: string
  student_name: string
  text: string
  time: string
  answer: string | null
  answer_time: string | null
}


