"""CoursePilot 后端入口。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import solver
from .models import Course, Offering, SolveResponse, StudentProfile, SwapRequest, SwapResponse

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"
from .academic import JsonAcademicDataSource
SEED = JsonAcademicDataSource(Path(os.getenv('COURSEPILOT_ACADEMIC_FILE', str(DATA_PATH)))).load()

COURSES: dict[str, Course] = {c["code"]: Course(**c) for c in SEED["courses"]}
OFFERINGS: list[Offering] = [Offering(**o) for o in SEED["offerings"]]

app = FastAPI(title="CoursePilot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "courses": len(COURSES), "offerings": len(OFFERINGS)}


@app.get("/api/bootstrap")
def bootstrap(request: Request = None) -> dict:
    """一次性返回前端渲染所需的基础数据。"""
    identity=getattr(request.state,'identity',None) if request else None
    record=SEED.get('students',{}).get(identity['username'],{}) if identity else {}
    completed=record.get('completed',SEED['completed'])
    major=record.get('major',SEED['major'])
    grade=record.get('grade',SEED['grade'])
    return {
        "term": SEED["term"],
        "major": major,
        "college": SEED.get("college", ""),
        "grade": grade,
        "notice": SEED["notice"],
        "completed": completed,
        "graduation": SEED.get("graduation", {}),
        "earned": record.get("earned",SEED.get("earned", {})),
        "plan": SEED["plan"],
        "requirements": SEED["requirements"],
        "courses": SEED["courses"],
        "offerings": SEED["offerings"],
        "default_profile": StudentProfile(
            major=major,
            grade=grade,
            completed=completed,
            interests=["系统", "AI", "工程"],
            goal="保研",
        ).model_dump(),
    }


@app.post("/api/solve", response_model=SolveResponse)
def solve(profile: StudentProfile) -> SolveResponse:
    """根据学生档案生成 Top-K 课表方案。"""
    return solver.solve(COURSES, OFFERINGS, SEED["plan"], profile, SEED.get("requirements"))


@app.post("/api/swap", response_model=SwapResponse)
def swap(req: SwapRequest) -> SwapResponse:
    """把课表中的某个教学班换成同课号的其他班次，并重新校验冲突。"""
    omap = {o.id: o for o in OFFERINGS}
    target = omap.get(req.target)
    replacement = omap.get(req.replacement)
    if target is None or replacement is None:
        return SwapResponse(ok=False, message="教学班不存在")
    if target.code != replacement.code:
        return SwapResponse(ok=False, message="只能在同一门课的不同班次之间切换")

    chosen: list[tuple[str, str]] = []
    for oid in req.offering_ids:
        off = omap.get(oid)
        if off is None:
            continue
        chosen.append((off.code, replacement.id if oid == req.target else oid))

    schedule, msg = solver.build_custom(chosen, COURSES, OFFERINGS, req.profile)
    if schedule is None:
        return SwapResponse(ok=False, message=msg)
    return SwapResponse(ok=True, schedule=schedule)


from .preferences import PreferenceText, extract_preference


@app.post("/api/preferences")
def preferences(request: PreferenceText) -> dict:
    return extract_preference(request, {tag for course in COURSES.values() for tag in course.tags})


from .community import router as community_router
app.include_router(community_router)

# Storage adapter injection: replace here when a database adapter is available.
import os
from .repository import JsonStudentRepository
from .personal import create_router
student_repository = JsonStudentRepository(Path(os.getenv('COURSEPILOT_STUDENT_DIR', str(DATA_PATH.parent / 'students'))))
from .llm_gateway import PersonalLLMProvider
from .auth import LocalIdentityStore, auth_router
from fastapi import Request
from fastapi.responses import JSONResponse
identity_store = LocalIdentityStore(Path(os.getenv('COURSEPILOT_AUTH_FILE', str(DATA_PATH.parent / 'auth.sqlite3'))))
app.include_router(auth_router(identity_store, secure=os.getenv('COURSEPILOT_SECURE_COOKIE')=='1'))

@app.middleware('http')
async def identity_boundary(request: Request, call_next):
    path=request.url.path
    # Reject cross-origin mutations, including login, before cookie authentication.
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'不允许跨站请求'},status_code=403)
    if path.startswith('/api/') and not path.startswith('/api/auth/') and path!='/api/health':
        identity=identity_store.resolve(request.cookies.get('coursepilot_session'))
        if not identity:return JSONResponse({'detail':'请先登录'},status_code=401)
        request.state.identity=identity
        if path.startswith('/api/students/'):
            student_id=path.split('/')[3]
            if student_id!=identity['student_id']:return JSONResponse({'detail':'不能访问其他学生档案'},status_code=403)
    return await call_next(request)

app.include_router(create_router(student_repository, COURSES, OFFERINGS, SEED, StudentProfile(**bootstrap()['default_profile']), provider=PersonalLLMProvider()))

# 教师端：预置教师账号（用户名=教师姓名，密码见 COURSEPILOT_TEACHER_PASSWORD，默认演示口令）
from . import teacher as teacher_module
for _name in sorted({o.teacher for o in OFFERINGS}):
    identity_store.register_teacher(_name, os.getenv('COURSEPILOT_TEACHER_PASSWORD', 'coursepilot2026'), _name)
app.include_router(teacher_module.teacher_router(COURSES, OFFERINGS))
app.include_router(teacher_module.public_router(COURSES, OFFERINGS))

# Serve the built workbench from the same origin as its API.
from fastapi.staticfiles import StaticFiles

frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="workbench")

