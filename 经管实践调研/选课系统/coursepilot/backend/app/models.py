"""数据模型定义：课程、教学班、培养计划与学生档案。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Session(BaseModel):
    """一次上课时段。day: 1-5 表示周一到周五；start/end 为节次。"""

    day: int = Field(ge=1, le=7)
    start: int = Field(ge=1, le=14)
    end: int = Field(ge=1, le=14)
    weeks: list[int] = Field(default_factory=lambda: list(range(1, 17)))
    location: str


class CourseProfile(BaseModel):
    """课程画像：由点评与大纲抽取的结构化字段，带样本量与置信度。"""

    weekly_hours: float
    difficulty: float
    grading: float
    style: str
    attendance: bool
    assessment: dict[str, int]
    sample_size: int
    confidence: float
    summary: str


class Course(BaseModel):
    code: str
    name: str
    credits: int
    category: str
    prereqs: list[str] = []
    tags: list[str] = []
    profile: CourseProfile


class Offering(BaseModel):
    """教学班：同一课号在不同学期/不同教师下的具体开课。"""

    id: str
    code: str
    teacher: str
    teacher_rating: float
    admit_rate: float
    capacity: int
    enrolled: int
    sessions: list[Session]


class PlanItem(BaseModel):
    code: str
    module: str
    suggest_term: int


class StudentProfile(BaseModel):
    """学生档案。三个滑杆均为 0..1。"""

    locked: list[str] = []
    excluded: list[str] = []
    blocked: list[Session] = []
    name: str = "同学"
    major: str = ""
    grade: int = 2024
    completed: list[str] = []
    interests: list[str] = []
    goal: str = "保研"
    # Learned from explicit interest feedback, bounded by the scorer.
    affinity: dict[str, float] = Field(default_factory=dict)
    # 0 = 分数优先，1 = 学到东西优先
    focus: float = 0.5
    # 0 = 轻松，1 = 挑战
    challenge: float = 0.5
    # 0 = 稳妥，1 = 探索
    exploration: float = 0.5
    avoid_early: bool = True
    min_credits: int = 18
    max_credits: int = 24


class CourseScore(BaseModel):
    code: str
    name: str
    credits: int
    total: float
    parts: dict[str, float]


class ScheduleItem(BaseModel):
    offering_id: str
    code: str
    name: str
    credits: int
    category: str
    teacher: str
    teacher_rating: float
    admit_rate: float
    sessions: list[Session]
    weekly_hours: float
    difficulty: float
    grading: float
    style: str
    summary: str
    tags: list[str]
    score: float
    contributions: dict[str, float]


class Schedule(BaseModel):
    id: str
    items: list[ScheduleItem]
    total_credits: int
    expected_credits: float
    total_weekly_hours: float
    avg_difficulty: float
    used_days: int
    score: float
    headline: str
    reasons: list[str]
    warnings: list[str]


class FrontierPoint(BaseModel):
    """权衡图上的一个可行解：用于展示「负荷—期望学分」的 Pareto 分布。"""

    credits: int
    hours: float
    expected: float
    difficulty: float
    score: float


class SolveResponse(BaseModel):
    schedules: list[Schedule]
    frontier: list[FrontierPoint] = []
    diagnostics: list[str] = []


class SwapRequest(BaseModel):
    """把某门课换成同一课号的另一个教学班。"""

    offering_ids: list[str]
    target: str
    replacement: str
    profile: StudentProfile


class SwapResponse(BaseModel):
    ok: bool
    schedule: Schedule | None = None
    message: str = ""
