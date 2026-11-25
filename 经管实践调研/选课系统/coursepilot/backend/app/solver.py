"""课表求解器：硬约束剪枝 + 效用打分 + 束搜索（Beam Search）。

设计要点：
1. 硬约束（时间冲突、学分区间、模块学分要求、先修）在搜索中直接剪枝，不进入打分。
2. 软目标拆成 5 个可解释维度，权重由学生档案的三个滑杆决定，因此每套方案都能讲清「为什么」。
3. 目标函数用「平均效用」而非总分，避免算法一味多塞课；再叠加负荷与碎片化惩罚。
4. 按模块分阶段搜索，在每个模块结束时强制满足该模块的最低学分要求。
"""

from __future__ import annotations

from typing import Iterable

from .models import (
    Course,
    CourseProfile,
    FrontierPoint,
    Offering,
    Schedule,
    ScheduleItem,
    SolveResponse,
    StudentProfile,
)

PERIOD_COUNT = 14
BEAM_WIDTH = 800
TOP_K = 3
DIVERSITY = 0.72  # 方案之间课程集合的 Jaccard 相似度上限
MODULES = ("必修", "专业选修", "通识")


# ---------------------------------------------------------------- 工具函数

def _clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


def _mask(sessions) -> int:
    """把上课时段编码成 5x14 的位图整数，用位运算做冲突检测。"""
    m = 0
    for s in sessions:
        for p in range(s.start, s.end + 1):
            for week in s.weeks:
                m |= 1 << (((week - 1) * 7 + s.day - 1) * PERIOD_COUNT + p - 1)
    return m


def _tag_match(interests: Iterable[str], tags: Iterable[str]) -> float:
    tags = list(tags)
    if not tags:
        return 0.35
    hit = sum(1 for t in tags if t in interests)
    if hit == 0:
        return 0.15
    return _clamp(0.45 + 0.55 * hit / len(tags))


def _load_cap(profile: StudentProfile) -> float:
    """学生每周可承受的课外投入上限。挑战偏好越高，上限越高。"""
    return 44.0 + 12.0 * profile.challenge


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------- 单课打分

def score_course(
    course: Course,
    offering: Offering,
    profile: StudentProfile,
) -> tuple[float, dict[str, float]]:
    """返回 (0-100 的效用分, 各维度对总分的贡献值)。

    维度定义（均为 0..1）：
      interest  兴趣匹配：专业标签与自选兴趣的交集
      comfort   负荷舒适：周均课外投入越低越高
      grading   给分友好度
      teaching  教师评分
      growth    难度匹配（最近发展区）：与「目标难度」的接近程度
    """
    p: CourseProfile = course.profile

    interest = _tag_match(profile.interests, course.tags)
    evidence = [max(-1.0, min(1.0, profile.affinity.get(t, 0.0))) for t in course.tags]
    if evidence:
        interest = _clamp(interest + 0.35 * sum(evidence) / len(evidence))
    comfort = 1.0 - _clamp((p.weekly_hours - 4.0) / 14.0)
    grading = _clamp((p.grading - 1.0) / 4.0)
    teaching = _clamp((offering.teacher_rating - 3.0) / 1.8)

    target_difficulty = 2.0 + 2.6 * profile.challenge
    growth = _clamp(1.0 - abs(p.difficulty - target_difficulty) / 2.5)

    dims = {
        "兴趣匹配": interest,
        "负荷舒适": comfort,
        "给分友好": grading,
        "教师口碑": teaching,
        "难度匹配": growth,
    }
    weights = {
        "兴趣匹配": 1.0,
        "负荷舒适": 0.5 + 1.3 * (1.0 - profile.challenge),
        "给分友好": 0.5 + 1.3 * (1.0 - profile.focus),
        "教师口碑": 0.9,
        "难度匹配": 0.5 + 1.3 * profile.focus,
    }

    total_w = sum(weights.values())
    contributions = {k: round(weights[k] * dims[k] / total_w * 100, 2) for k in dims}
    total = sum(contributions.values())

    # 早八惩罚：作为时间成本直接扣减
    if profile.avoid_early and min(s.start for s in offering.sessions) <= 2:
        total -= 4.0

    # 中签风险：偏向「稳妥」时奖励高概率课，偏向「探索」时轻微容忍低概率课
    if profile.exploration < 0.5:
        total += (0.5 - profile.exploration) * 2 * (offering.admit_rate - 0.5) * 10
    else:
        total += (profile.exploration - 0.5) * 2 * (0.35 - offering.admit_rate) * 8

    return round(max(0.0, min(100.0, total)), 2), contributions


# ---------------------------------------------------------------- 主求解

def solve(
    courses: dict[str, Course],
    offerings: list[Offering],
    plan: list[dict],
    profile: StudentProfile,
    requirements: list[dict] | None = None,
    top_k: int = TOP_K,
) -> SolveResponse:
    completed = set(profile.completed)
    diagnostics: list[str] = []

    req: dict[str, int] = {m: 0 for m in MODULES}
    for r in requirements or []:
        if r.get("module") in req:
            req[r["module"]] = int(r.get("min_credits", 0))

    by_code: dict[str, list[Offering]] = {}
    locked = {o.code: o.id for o in offerings if o.id in profile.locked}
    if len(locked) != len(set(profile.locked)):
        return SolveResponse(schedules=[], diagnostics=["锁定班号无效或同一门课锁定了两个班"])
    blocked = _mask(profile.blocked)
    for o in offerings:
        if o.id in profile.excluded or locked.get(o.code, o.id) != o.id or _mask(o.sessions) & blocked:
            continue
        by_code.setdefault(o.code, []).append(o)

    # ---- 候选课程：本学期计划内、未修、先修满足
    candidates: list[tuple[str, bool, str]] = []  # (模块, 是否必修, 课号)
    for item in plan:
        code = item["code"]
        module = item.get("module", "通识")
        course = courses.get(code)
        if module in req and code in completed and course and module == "必修":
            req[module] = max(0, req[module] - course.credits)
        if course is None or code in completed:
            continue
        if not all(p in completed for p in course.prereqs):
            diagnostics.append(f"{course.name} 先修未满足，已跳过")
            continue
        if code not in by_code:
            diagnostics.append(f"{course.name} 本学期未开课，已跳过")
            continue
        candidates.append((module, module == "必修", code))

    needed = {r["code"] for r in plan if r["module"] == "必修"} - completed
    missing = (needed | set(locked)) - {entry[2] for entry in candidates}
    if missing:
        return SolveResponse(schedules=[], diagnostics=["必修或锁定课程缺少可用班次，请核对先修、禁排时段与满员记录：" + "、".join(sorted(missing))])
    if not candidates:
        return SolveResponse(schedules=[], diagnostics=diagnostics or ["没有可选的课程"])

    candidates.sort(
        key=lambda x: (MODULES.index(x[0]) if x[0] in MODULES else 9, not x[1], -courses[x[2]].credits, x[2])
    )

    # ---- 预算每个教学班的效用
    scored: dict[str, list[tuple[Offering, int, float, dict[str, float]]]] = {}
    for _, _, code in candidates:
        rows = []
        for off in by_code[code]:
            total, parts = score_course(courses[code], off, profile)
            rows.append((off, _mask(off.sessions), total, parts))
        rows.sort(key=lambda r: -r[2])
        scored[code] = rows

    cap = _load_cap(profile)

    # ---- 束搜索
    # 状态：(位图, 总学分, 周投入, 效用累计, 各模块学分, 已选 ((课号, offering_id), ...))
    State = tuple[int, int, float, float, tuple[int, int, int], tuple[tuple[str, str], ...]]
    beam: list[State] = [(0, 0, 0.0, 0.0, (0, 0, 0), ())]

    for idx, (module, is_mandatory, code) in enumerate(candidates):
        course = courses[code]
        mi = MODULES.index(module) if module in MODULES else 2
        nxt: list[State] = []
        for mask, credits, hours, util, mods, chosen in beam:
            if not is_mandatory and code not in locked:
                nxt.append((mask, credits, hours, util, mods, chosen))
            for off, omask, oscore, _ in scored[code]:
                if mask & omask:
                    continue
                nc = credits + course.credits
                if nc > profile.max_credits:
                    continue
                nh = hours + course.profile.weekly_hours
                nmods = list(mods)
                nmods[mi] += course.credits
                nxt.append((mask | omask, nc, nh, util + oscore, tuple(nmods), chosen + ((code, off.id),)))

        if not nxt:
            diagnostics.append("必修课之间存在时间冲突，无法生成完整课表")
            return SolveResponse(schedules=[], diagnostics=diagnostics)

        nxt.sort(key=lambda s: -_rank(s, cap))
        beam = nxt[:BEAM_WIDTH]

        # 模块边界：强制满足该模块的最低学分
        last_of_module = idx == len(candidates) - 1 or candidates[idx + 1][0] != module
        if last_of_module and req.get(module, 0) > 0:
            ok = [s for s in beam if s[4][mi] >= req[module]]
            if ok:
                beam = ok
            else:
                diagnostics.append(f"{module} 无法满足最低 {req[module]} 学分要求")

    # ---- 最终可行性过滤
    def complete(s) -> bool:
        return (
            profile.min_credits <= s[1] <= profile.max_credits
            and all(s[4][i] >= req[m] for i, m in enumerate(MODULES))
        )

    feasible = [s for s in beam if complete(s)]
    if not feasible:
        return SolveResponse(schedules=[], diagnostics=diagnostics + ["当前搜索未找到同时满足学分、模块和时段的方案，请调整限制后重试。"])

    feasible.sort(key=lambda s: -_rank(s, cap))

    # ---- 取 Top-K，并强制方案之间有足够差异
    picked: list[State] = []
    picked_sets: list[frozenset] = []
    for st in feasible:
        code_set = frozenset(c for c, _ in st[5])
        if any(_jaccard(code_set, prev) >= DIVERSITY for prev in picked_sets):
            continue
        picked.append(st)
        picked_sets.append(code_set)
        if len(picked) >= top_k:
            break
    if not picked:
        picked = feasible[:1]

    schedules = [
        _build_schedule(i, state, courses, offerings, profile, cap)
        for i, state in enumerate(picked)
    ]
    return SolveResponse(
        schedules=schedules,
        frontier=_frontier(feasible, courses, offerings),
        diagnostics=diagnostics,
    )


def _frontier(states, courses: dict[str, Course], offerings: list[Offering]) -> list[FrontierPoint]:
    """把可行解投影到「周投入 × 期望学分」平面上，供前端画权衡图。"""
    omap = {o.id: o for o in offerings}
    best: dict[tuple[int, int], FrontierPoint] = {}
    for st in states:
        credits, hours, chosen = st[1], st[2], st[5]
        if not chosen:
            continue
        expected = sum(omap[oid].admit_rate * courses[code].credits for code, oid in chosen)
        diff = sum(courses[code].profile.difficulty for code, _ in chosen) / len(chosen)
        key = (credits, round(hours))
        point = FrontierPoint(
            credits=credits,
            hours=round(hours, 1),
            expected=round(expected, 1),
            difficulty=round(diff, 2),
            score=round(_rank(st, 1e9), 1),
        )
        if key not in best or point.score > best[key].score:
            best[key] = point
    return sorted(best.values(), key=lambda p: -p.score)[:60]


def build_custom(
    chosen: list[tuple[str, str]],
    courses: dict[str, Course],
    offerings: list[Offering],
    profile: StudentProfile,
) -> tuple[Schedule | None, str]:
    """按指定的教学班组合重建一套课表，用于「换班次」。"""
    omap = {o.id: o for o in offerings}
    mask = 0
    credits = 0
    hours = 0.0
    util = 0.0
    for code, oid in chosen:
        off = omap.get(oid)
        course = courses.get(code)
        if off is None or course is None:
            return None, "教学班不存在"
        m = _mask(off.sessions)
        if mask & m:
            return None, f"{course.name}（{off.teacher}）与已有课程时间冲突"
        mask |= m
        credits += course.credits
        hours += course.profile.weekly_hours
        score, _ = score_course(course, off, profile)
        util += score

    state = (mask, credits, hours, util, (0, 0, 0), tuple(chosen))
    return _build_schedule(0, state, courses, offerings, profile, _load_cap(profile)), ""


def _rank(state, cap: float) -> float:
    """束搜索与最终排序共用的标量目标。"""
    _, _, hours, util, _, chosen = state
    if not chosen:
        return 0.0
    mean_u = util / len(chosen)
    return mean_u - 1.0 * max(0.0, hours - cap)


# ---------------------------------------------------------------- 结果组装

def _build_schedule(
    idx: int,
    state,
    courses: dict[str, Course],
    offerings: list[Offering],
    profile: StudentProfile,
    cap: float,
) -> Schedule:
    _, credits, hours, _, _, chosen = state
    omap = {o.id: o for o in offerings}

    items: list[ScheduleItem] = []
    for code, oid in chosen:
        course = courses[code]
        off = omap[oid]
        score, parts = score_course(course, off, profile)
        items.append(
            ScheduleItem(
                offering_id=off.id,
                code=code,
                name=course.name,
                credits=course.credits,
                category=course.category,
                teacher=off.teacher,
                teacher_rating=off.teacher_rating,
                admit_rate=off.admit_rate,
                sessions=off.sessions,
                weekly_hours=course.profile.weekly_hours,
                difficulty=course.profile.difficulty,
                grading=course.profile.grading,
                style=course.profile.style,
                summary=course.profile.summary,
                tags=course.tags,
                score=score,
                contributions=parts,
            )
        )

    used_days, gaps = _time_shape(items)
    expected = sum(i.credits * i.admit_rate for i in items)
    avg_diff = sum(i.difficulty for i in items) / len(items)
    mean_u = sum(i.score for i in items) / len(items)
    final = mean_u - max(0.0, hours - cap) + (5 - used_days) * 1.2 - gaps * 0.25

    return Schedule(
        id=f"plan-{idx + 1}",
        items=items,
        total_credits=credits,
        expected_credits=round(expected, 1),
        total_weekly_hours=round(hours, 1),
        avg_difficulty=round(avg_diff, 2),
        used_days=used_days,
        score=round(final, 1),
        headline=_headline(items, avg_diff, hours, cap, profile),
        reasons=_reasons(items, credits, used_days, gaps, avg_diff, profile),
        warnings=_warnings(items, credits, hours, expected, cap, profile),
    )


def _time_shape(items: list[ScheduleItem]) -> tuple[int, int]:
    """返回 (上课天数, 空档节数)。空档用于评估课表的碎片化程度。"""
    days: dict[int, set[int]] = {}
    for it in items:
        for s in it.sessions:
            days.setdefault(s.day, set()).update(range(s.start, s.end + 1))
    gaps = 0
    for periods in days.values():
        gaps += (max(periods) - min(periods) + 1) - len(periods)
    return len(days), gaps


def _headline(items, avg_diff, hours, cap, profile) -> str:
    """用「特征 + 代表课」命名方案，保证三套方案彼此可区分。"""
    # 用「非必修」中得分最高的一门作为代表课，让三套方案彼此可区分
    pool = [i for i in items if i.category != "必修"] or items
    rep = max(pool, key=lambda i: i.score).name
    if avg_diff >= 4.0:
        trait = "硬核方案"
    elif hours > cap + 4:
        trait = "高负荷方案"
    elif avg_diff <= 3.3:
        trait = "均衡方案"
    elif len([i for i in items if i.difficulty >= 4.0]) >= 2:
        trait = "进阶方案"
    else:
        trait = "稳健方案"
    return f"{trait} · {rep}"


def _reasons(items, credits, used_days, gaps, avg_diff, profile) -> list[str]:
    n_must = sum(1 for i in items if i.category == "必修")
    n_major = sum(1 for i in items if i.category == "专业选修")
    n_ge = sum(1 for i in items if i.category == "通识")
    out: list[str] = [
        f"覆盖 {n_must} 门必修 + {n_major} 门专业选修 + {n_ge} 门通识，共 {credits} 学分"
    ]

    top = max(items, key=lambda i: max(i.contributions.values()))
    dim = max(top.contributions, key=top.contributions.get)
    out.append(f"{top.name} 是这套方案的支点：{dim}贡献最高（{top.contributions[dim]} 分）")

    if used_days <= 4:
        out.append(f"一周只上 {used_days} 天课，通勤与自习时间更整块")
    if gaps <= 3:
        out.append("课表空档很少，白天的时间块完整")
    if avg_diff < 3.6:
        out.append("整体难度控制在中等，学期中段不容易同时爆作业")
    elif avg_diff >= 4.0:
        out.append("整体偏硬核，适合本学期集中突破专业课")
    if profile.avoid_early and all(min(s.start for s in i.sessions) > 2 for i in items):
        out.append("全部避开了早八")
    return out


def _warnings(items, credits, hours, expected, cap, profile) -> list[str]:
    out: list[str] = []
    risky = [i for i in items if i.admit_rate < 0.35]
    if risky:
        names = "、".join(i.name for i in risky[:3])
        out.append(f"{names} 历史中签率低于 35%，海选需搭配保底志愿")
    if hours > cap + 8:
        out.append(f"预计周课外投入 {hours:.0f} 小时，明显高于你的承受线 {cap:.0f} 小时")
    if credits < profile.min_credits:
        out.append(f"当前 {credits} 学分，低于最低要求 {profile.min_credits}")
    early = [i for i in items if profile.avoid_early and min(s.start for s in i.sessions) <= 2]
    if early:
        out.append(f"{len(early)} 门课含早八（受班次限制，已按偏好尽量避开）")
    if expected < credits * 0.65:
        out.append(f"按历史中签率折算，期望只能拿到约 {expected:.1f} 学分")
    return out
