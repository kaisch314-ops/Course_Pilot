"""教师端：AI 总结（规则占位 + 预留 LLM）、课程简介、师生问答、学生偏好聚合。

数据存于 data/coursepilot.db（BCNF 关系库）。AI 接口与学生端 preferences.py 同款设计：
默认本地规则生成，配置 COURSEPILOT_LLM_BASE_URL / COURSEPILOT_LLM_MODEL /
COURSEPILOT_LLM_TOKEN 后切换到 OpenAI 兼容接口，失败自动回退规则。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "coursepilot.db"
STUDENT_DIR = Path(__file__).resolve().parent.parent / "data" / "students"
MIN_SAMPLE = 5  # 匿名聚合最小样本量（与文档承诺一致）

TOPICS = {
    "课外投入": re.compile(r"小时|作业|课后|每周| workload|负担"),
    "考核方式": re.compile(r"考试|开卷|闭卷|论文|报告|pre|展示|汇报|答辩", re.I),
    "给分": re.compile(r"给分|分数|绩点|GPA|捞", re.I),
    "点名考勤": re.compile(r"点名|签到|考勤"),
    "课堂互动": re.compile(r"提问|互动|发言|讨论"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_schema(db_path: Path | None = None) -> None:
    db = sqlite3.connect(db_path or DB_PATH)
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS teacher_intro (
            teacher TEXT NOT NULL, course_code TEXT NOT NULL,
            style TEXT NOT NULL DEFAULT '', attendance TEXT NOT NULL DEFAULT '',
            assessment TEXT NOT NULL DEFAULT '', expectation TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL, PRIMARY KEY (teacher, course_code))""")
        db.execute("""CREATE TABLE IF NOT EXISTS qa_question (
            id TEXT PRIMARY KEY, course_code TEXT NOT NULL, teacher TEXT NOT NULL,
            student_id TEXT NOT NULL, student_name TEXT NOT NULL,
            text TEXT NOT NULL, time TEXT NOT NULL,
            answer TEXT, answer_time TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS ai_summary_cache (
            teacher TEXT NOT NULL, course_code TEXT NOT NULL, kind TEXT NOT NULL,
            content TEXT NOT NULL, source TEXT NOT NULL, generated_at TEXT NOT NULL,
            PRIMARY KEY (teacher, course_code, kind))""")


# ---------------- AI 提供方：规则占位 + 预留 LLM ----------------

class TeacherAI:
    """与学生端 preferences.py 同一哲学：默认本地规则，LLM 仅作可选增强。"""

    def __init__(self):
        self.base_url = os.getenv("COURSEPILOT_LLM_BASE_URL", "").rstrip("/")
        self.model = os.getenv("COURSEPILOT_LLM_MODEL", "")
        self.token = os.getenv("COURSEPILOT_LLM_TOKEN", "")

    @property
    def llm_ready(self) -> bool:
        return bool(self.base_url and self.model and self.token)

    def summarize(self, kind: str, teacher: str, course_name: str, facts: dict) -> tuple[str, str]:
        """返回 (文本, 来源)。来源 ∈ rules / llm。"""
        if self.llm_ready:
            try:
                return self._llm(kind, teacher, course_name, facts), "llm"
            except Exception:
                pass  # 回退规则，绝不把异常暴露给教师
        return self._rules(kind, teacher, course_name, facts), "rules"

    def _llm(self, kind: str, teacher: str, course_name: str, facts: dict) -> str:
        titles = {"reviews": "选课社区评价总结", "preferences": "学生偏好分析", "advice": "教学改进建议"}
        prompt = (
            f"你是高校教学助手。请根据以下事实数据，为《{course_name}》的任课教师{teacher}生成一段"
            f"「{titles[kind]}」。要求：只依据给定事实，不编造评价；分 3-5 条要点；语气中立、对事不对人。\n"
            f"事实数据：{json.dumps(facts, ensure_ascii=False)}"
        )
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False}
        req = Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.token})
        with urlopen(req, timeout=20) as res:
            data = json.load(res)
        return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _rules(kind: str, teacher: str, course_name: str, facts: dict) -> str:
        p = facts.get("profile") or {}
        comm = facts.get("community") or {}
        pref = facts.get("preferences") or {}
        lines: list[str] = []
        if kind == "reviews":
            if comm.get("matched"):
                lines.append(f"选课社区共检索到 {comm['matched']} 门您授课的相关课程页面："
                             f"平均评分 {comm['average']}（{comm['count']} 人评分）。")
                if comm.get("topics"):
                    topics = "、".join(f"{k}（{v} 条提及）" for k, v in comm["topics"].items())
                    lines.append(f"近十条评价的高频主题：{topics}。")
                if comm.get("snippets"):
                    lines.append("代表性评价摘录：" + "；".join(comm["snippets"]))
            else:
                lines.append("选课社区暂无匹配到您姓名的课程评价（可能缺少 API Key 或社区未收录）。")
            if p:
                lines.append(f"系统内演示画像：示例难度 {p.get('difficulty')}、示例给分 {p.get('grading')}、"
                             f"示例周投入 {p.get('weekly_hours')} 小时（演示数据，不代表真实反馈）。")
        elif kind == "preferences":
            if pref.get("insufficient"):
                lines.append(f"目前只有 {pref.get('contributors', 0)} 名学生的偏好数据涉及本课程，"
                             f"少于最小展示单元 {MIN_SAMPLE} 人。为保护学生隐私，暂不展示聚合结论。")
            else:
                lines.append(f"{pref['contributors']} 名学生的偏好数据涉及本课程。")
                if pref.get("interest_hits"):
                    lines.append("与本课程标签重合的学生兴趣：" + "、".join(pref["interest_hits"]) + "。")
                lines.append(f"学生滑杆均值：专注 {pref.get('focus')} / 挑战 {pref.get('challenge')} / 探索 {pref.get('exploration')}。")
                if pref.get("feedback"):
                    lines.append("学生显式反馈：" + "；".join(pref["feedback"]))
        else:  # advice
            if p:
                if (p.get("weekly_hours") or 0) >= 7:
                    lines.append("课外投入示例值偏高（≥7 小时/周）：可在教学大纲中拆出“选做”层次，或在第一周明确时间预算，降低学生的心理门槛。")
                if p.get("attendance"):
                    lines.append("本课程有点名：建议在第一周说明点名的目的（如案例讨论需要出勤），避免学生因未知规则而回避选课。")
                if (p.get("grading") or 5) < 3.5:
                    lines.append("给分画像示例值偏低：学生端最敏感的因素是给分透明度，建议在课程简介中写清评分构成与历年中位表现。")
                if (p.get("difficulty") or 0) >= 3.5:
                    lines.append("难度示例值偏高：可提供先修自查清单与助教答疑时段，把“难”转化为“可预期的挑战”。")
            fill = facts.get("fill_rate")
            if fill is not None and fill < 0.7:
                lines.append(f"当前班次选中率约 {fill:.0%}：建议完善课程简介（教学方式、考核、期望学生），信息不对称是学生放弃选课的首要原因。")
            elif fill is not None and fill >= 1:
                lines.append("班次已满员：选课需求旺盛，可考虑向教务反馈扩班依据。")
            if comm.get("topics", {}).get("课外投入"):
                lines.append("社区评价中“课外投入”被频繁提及：建议在简介中如实说明每周时间预算，透明反而能稳定选课意愿。")
            if not lines:
                lines.append("暂无足够数据生成建议。积累社区评价与简介后可获得更具体的分析。")
        return "\n".join("· " + line for line in lines)


# ---------------- 事实采集 ----------------

def collect_facts(course: dict, offerings: list[dict], teacher: str) -> dict:
    facts: dict = {}
    p = course.get("profile") or {}
    facts["profile"] = {"difficulty": p.get("difficulty"), "grading": p.get("grading"),
                        "weekly_hours": p.get("weekly_hours"), "attendance": p.get("attendance")}
    mine = [o for o in offerings if o["teacher"] == teacher and o["code"] == course["code"]]
    if mine:
        total_cap = sum(o.get("capacity") or 0 for o in mine)
        total_enr = sum(o.get("enrolled") or 0 for o in mine)
        facts["fill_rate"] = (total_enr / total_cap) if total_cap else None

    # 社区评价（可选，需要 JCOURSE_API_KEY）
    community: dict = {}
    try:
        from . import community as jc
        rows = [jc.course(r) for r in jc.fetch("/course/", q=course["name"], page_size=10)["items"]]
        matched = [r for r in rows if r.get("teacher") == teacher][:3]
        if matched:
            total_count = sum(r.get("count") or 0 for r in matched)
            weighted = sum((r.get("average") or 0) * (r.get("count") or 0) for r in matched)
            community = {"matched": len(matched), "count": total_count,
                         "average": round(weighted / total_count, 2) if total_count else None}
            topics: dict[str, int] = {}
            snippets: list[str] = []
            first = matched[0]
            data = jc.fetch(f"/course/{first['id']}/review", order_by="created_at", page_size=10)
            for r in data["items"]:
                text = (r.get("content") or "")[:2000]
                for name, pattern in TOPICS.items():
                    if pattern.search(text):
                        topics[name] = topics.get(name, 0) + 1
                if text.strip() and len(snippets) < 2:
                    snippets.append("「" + text.strip()[:80] + "…」")
            community["topics"] = dict(sorted(topics.items(), key=lambda kv: -kv[1]))
            community["snippets"] = snippets
    except HTTPException:
        community = {}
    except Exception:
        community = {}
    facts["community"] = community

    # 学生偏好聚合（只读 students/*.json，遵循最小样本量规则）
    contributors: set[str] = set()
    focus, challenge, exploration = [], [], []
    interest_hits: dict[str, int] = {}
    feedback_notes: list[str] = []
    tags = set(course.get("tags") or [])
    if STUDENT_DIR.is_dir():
        for path in STUDENT_DIR.glob("*.json"):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            prof = doc.get("profile") or {}
            relevant = bool(tags & set(prof.get("interests") or []))
            fb = [f for f in doc.get("feedback") or [] if f.get("course") == course["code"]]
            if not relevant and not fb:
                continue
            contributors.add(doc.get("id") or path.stem)
            for key, bucket in (("focus", focus), ("challenge", challenge), ("exploration", exploration)):
                if isinstance(prof.get(key), (int, float)):
                    bucket.append(prof[key])
            for t in tags & set(prof.get("interests") or []):
                interest_hits[t] = interest_hits.get(t, 0) + 1
            for f in fb:
                direction = "偏好" if f.get("direction") == 1 else "劝退"
                feedback_notes.append(f"{direction}（{f.get('reason', '未注明原因')}）")
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    facts["preferences"] = {
        "contributors": len(contributors),
        "insufficient": len(contributors) < MIN_SAMPLE,
        "focus": avg(focus), "challenge": avg(challenge), "exploration": avg(exploration),
        "interest_hits": sorted(interest_hits, key=interest_hits.get, reverse=True) if interest_hits else [],
        "feedback": feedback_notes if len(contributors) >= MIN_SAMPLE else [],
    }
    return facts


# ---------------- 路由 ----------------

class IntroBody(BaseModel):
    course_code: str
    style: str = Field(default="", max_length=2000)
    attendance: str = Field(default="", max_length=1000)
    assessment: str = Field(default="", max_length=1000)
    expectation: str = Field(default="", max_length=1000)


class QuestionBody(BaseModel):
    course_code: str
    teacher: str
    text: str = Field(min_length=2, max_length=1000)


class AnswerBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def teacher_router(courses: dict, offerings: list) -> APIRouter:
    router = APIRouter(prefix="/api/teacher", tags=["teacher"])
    ai = TeacherAI()
    init_schema()

    def teacher_of(request: Request) -> str:
        identity = getattr(request.state, "identity", None) or {}
        if identity.get("role") != "teacher" or not identity.get("teacher_name"):
            raise HTTPException(403, "仅教师账号可用")
        return identity["teacher_name"]

    def my_courses(name: str) -> list[str]:
        return sorted({o.code for o in offerings if o.teacher == name})

    @router.get("/me")
    def me(request: Request):
        name = teacher_of(request)
        result = []
        for code in my_courses(name):
            c = courses[code]
            result.append({
                "code": code, "name": c.name, "credits": c.credits,
                "offerings": [{"id": o.id, "capacity": o.capacity, "enrolled": o.enrolled}
                              for o in offerings if o.code == code and o.teacher == name],
            })
        return {"teacher_name": name, "courses": result,
                "llm_ready": ai.llm_ready}

    @router.get("/summary")
    def summary(request: Request, course: str):
        name = teacher_of(request)
        if course not in my_courses(name):
            raise HTTPException(403, "只能查看本人授课课程")
        c = courses[course]
        db = connect()
        cached = {r["kind"]: dict(r) for r in db.execute(
            "SELECT * FROM ai_summary_cache WHERE teacher=? AND course_code=?", (name, course))}
        if len(cached) == 3:
            db.close()
            return {"course": course, "cached": True,
                    "kinds": {k: {"content": v["content"], "source": v["source"],
                                  "generated_at": v["generated_at"]} for k, v in cached.items()}}
        facts = collect_facts(c.model_dump(), [o.model_dump() for o in offerings], name)
        kinds: dict[str, dict] = {}
        with db:
            for kind in ("reviews", "preferences", "advice"):
                text, source = ai.summarize(kind, name, c.name, facts)
                db.execute("INSERT OR REPLACE INTO ai_summary_cache VALUES (?,?,?,?,?,?)",
                           (name, course, kind, text, source, now()))
                kinds[kind] = {"content": text, "source": source, "generated_at": now()}
        db.close()
        return {"course": course, "cached": False, "kinds": kinds}

    @router.post("/summary/refresh")
    def refresh(request: Request, course: str):
        name = teacher_of(request)
        with connect() as db:
            db.execute("DELETE FROM ai_summary_cache WHERE teacher=? AND course_code=?", (name, course))
        return summary(request, course)

    @router.get("/intro")
    def get_intro(request: Request, course: str):
        name = teacher_of(request)
        db = connect()
        row = db.execute("SELECT * FROM teacher_intro WHERE teacher=? AND course_code=?",
                         (name, course)).fetchone()
        db.close()
        return dict(row) if row else {"teacher": name, "course_code": course, "style": "",
                                      "attendance": "", "assessment": "", "expectation": ""}

    @router.put("/intro")
    def put_intro(request: Request, body: IntroBody):
        name = teacher_of(request)
        if body.course_code not in my_courses(name):
            raise HTTPException(403, "只能编辑本人授课课程")
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO teacher_intro VALUES (?,?,?,?,?,?,?)",
                       (name, body.course_code, body.style, body.attendance,
                        body.assessment, body.expectation, now()))
        return {"saved": True}

    @router.get("/qa")
    def my_qa(request: Request):
        name = teacher_of(request)
        db = connect()
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM qa_question WHERE teacher=? ORDER BY answer_time IS NOT NULL, time DESC",
            (name,))]
        db.close()
        return rows

    @router.post("/qa/{qid}/answer")
    def answer(request: Request, qid: str, body: AnswerBody):
        name = teacher_of(request)
        with connect() as db:
            row = db.execute("SELECT teacher FROM qa_question WHERE id=?", (qid,)).fetchone()
            if not row or row["teacher"] != name:
                raise HTTPException(404, "问题不存在或不属于您")
            db.execute("UPDATE qa_question SET answer=?, answer_time=? WHERE id=?",
                       (body.text, now(), qid))
        return {"answered": True}

    return router


def public_router(courses: dict, offerings: list) -> APIRouter:
    """学生端可见的课程简介与问答。"""
    router = APIRouter(prefix="/api", tags=["qa"])

    @router.get("/intro")
    def intro(course: str):
        if course not in courses:
            raise HTTPException(404, "课程不存在")
        db = connect()
        rows = [dict(r) for r in db.execute(
            "SELECT teacher, style, attendance, assessment, expectation, updated_at "
            "FROM teacher_intro WHERE course_code=?", (course,))]
        db.close()
        teachers = sorted({o.teacher for o in offerings if o.code == course})
        return {"course": course, "teachers": teachers, "intros": rows}

    @router.get("/qa")
    def qa_list(course: str):
        if course not in courses:
            raise HTTPException(404, "课程不存在")
        db = connect()
        rows = [dict(r) for r in db.execute(
            "SELECT id, teacher, student_name, text, time, answer, answer_time "
            "FROM qa_question WHERE course_code=? ORDER BY time DESC", (course,))]
        db.close()
        return rows

    @router.post("/qa")
    def ask(request: Request, body: QuestionBody):
        identity = getattr(request.state, "identity", None) or {}
        if identity.get("role") == "teacher":
            raise HTTPException(403, "教师请使用教师端回复功能")
        if body.course_code not in courses:
            raise HTTPException(404, "课程不存在")
        teachers = {o.teacher for o in offerings if o.code == body.course_code}
        if body.teacher not in teachers:
            raise HTTPException(400, "该教师未开设此课程")
        with connect() as db:
            db.execute("INSERT INTO qa_question VALUES (?,?,?,?,?,?,?,NULL,NULL)",
                       (str(uuid4()), body.course_code, body.teacher,
                        identity.get("student_id") or "", identity.get("username") or "匿名",
                        body.text, now()))
        return {"asked": True}

    return router
