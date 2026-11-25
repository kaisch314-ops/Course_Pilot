# -*- coding: utf-8 -*-
"""CoursePilot 陈氏 ER 图：实体方框 / 属性椭圆 / 主码下划线 / 多值双椭圆 / 弱实体双框"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, Polygon
import matplotlib.font_manager as fm

_FONTS = "/Users/kaisen/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/fonts"
for f in ("NotoSansCJKsc-Regular.otf", "NotoSansCJKsc-Bold.otf"):
    fm.fontManager.addfont(f"{_FONTS}/{f}")
plt.rcParams["font.family"] = ["Noto Sans CJK SC"]

INK = "#1B1F24"; ACC = "#7D3C98"; GOLD = "#B7950B"; RED = "#B03A2E"

def _ulen(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

class ER:
    def __init__(self, w_in, h_in, xlim, ylim):
        self.fig, self.ax = plt.subplots(figsize=(w_in, h_in))
        self.ax.set_xlim(0, xlim); self.ax.set_ylim(0, ylim)
        self.ax.axis("off"); self.xlim = xlim; self.ylim = ylim
        self.underlines = []  # (text_handle, dashed)

    def entity(self, x, y, name, weak=False, w=7.5, h=3.0):
        if weak:
            self.ax.add_patch(Rectangle((x - w/2 - 0.5, y - h/2 - 0.5), w + 1, h + 1,
                                        fill=False, ec=INK, lw=1.2))
        self.ax.add_patch(Rectangle((x - w/2, y - h/2), w, h, fc="white", ec=INK, lw=1.4, zorder=3))
        self.ax.text(x, y, name, ha="center", va="center", fontsize=12.5, weight="bold", zorder=4)

    def diamond(self, x, y, name, weak=False, w=9, h=3.6):
        pts = [(x, y + h/2), (x + w/2, y), (x, y - h/2), (x - w/2, y)]
        if weak:
            s = 1.22
            pts2 = [(x + (px - x) * s, y + (py - y) * s) for px, py in pts]
            self.ax.add_patch(Polygon(pts2, closed=True, fill=False, ec=GOLD, lw=1.1))
        self.ax.add_patch(Polygon(pts, closed=True, fc="#FCF3CF", ec=GOLD, lw=1.3, zorder=3))
        self.ax.text(x, y, name, ha="center", va="center", fontsize=10.5, color="#7D6608", zorder=4)

    def edge(self, x1, y1, x2, y2, label=None, dash=False, color=INK, lx=0, ly=0.7):
        self.ax.plot([x1, x2], [y1, y2], color=color, lw=1.1,
                     ls="--" if dash else "-", zorder=1)
        if label:
            self.ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label,
                         fontsize=9.5, ha="center", color=color)

    def attr(self, ex, ey, x, y, name, key=False, multi=False, partial=False,
             fs=9.5, connect=True, color=INK):
        u = _ulen(name)
        w = 0.62 * u + 2.2
        h = 1.7 + 0.12 * (fs - 9.5)
        if multi:
            self.ax.add_patch(Ellipse((x, y), w * 1.16, h * 1.32, fill=False, ec=INK, lw=1.0, zorder=3))
        self.ax.add_patch(Ellipse((x, y), w, h, fc="white", ec=INK, lw=1.1, zorder=3))
        t = self.ax.text(x, y, name, ha="center", va="center", fontsize=fs, zorder=4, color=color)
        if connect:
            self.edge(ex, ey, x, y)
        if key or partial:
            self.underlines.append((t, partial))
        return x, y

    def finish(self, path, title=None):
        if title:
            self.ax.text(self.xlim / 2, self.ylim - 1.2, title, fontsize=16,
                         weight="bold", ha="center")
        self.fig.canvas.draw()
        r = self.fig.canvas.get_renderer()
        inv = self.ax.transData.inverted()
        for t, dashed in self.underlines:
            bb = t.get_window_extent(renderer=r)
            (x0, _), (x1, _) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y0)])
            y = inv.transform([(bb.x0, bb.y0 - 2)])[0][1]
            self.ax.plot([x0, x1], [y, y], color=INK, lw=1.2, ls=(0, (2, 1.5)) if dashed else "-")
        self.fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(self.fig)
        print(path)

import math

def ring(er, ex, ey, names, rx, ry, start=90, span=360, **kw):
    """把属性均匀摆在实体周围一圈。names: (label, kind)"""
    n = len(names)
    out = {}
    for i, (label, kind) in enumerate(names):
        ang = math.radians(start - span * i / n)
        x = ex + rx * math.cos(ang); y = ey + ry * math.sin(ang)
        er.attr(ex, ey, x, y, label,
                key=(kind == "key"), multi=(kind == "multi"),
                partial=(kind == "partial"))
        out[label] = (x, y)
    return out

# ============ 图 1：参考库实体属性 ============
er = ER(20, 13, 100, 62)

# --- COURSE（含复合属性 profile） ---
CX, CY = 27, 40
er.entity(CX, CY, "课程 COURSE")
pos = ring(er, CX, CY, [("课号 code", "key"), ("名称 name", ""), ("学分 credits", ""),
                        ("类别 category", ""), ("标签 tags", "multi"), ("先修课 prereqs", "multi")],
           rx=16, ry=11, start=95, span=300)
# 复合属性 profile
px, py = er.attr(CX, CY, CX + 19, CY - 6, "画像 profile")
kids = [("周学时 weekly_hours", ""), ("难度 difficulty", ""), ("给分 grading", ""),
        ("风格 style", ""), ("点名 attendance", ""), ("样本量 sample_size", ""),
        ("置信度 confidence", ""), ("摘要 summary", "")]
n = len(kids)
for i, (label, kind) in enumerate(kids):
    ang = math.radians(75 - 150 * i / (n - 1))
    kx = px + 15 * math.cos(ang); ky = py - 1 + 10 * math.sin(ang)
    er.attr(px, py, kx, ky, label)
# assessment 二级复合（嵌套在 profile 下）
ax_, ay_ = er.attr(px, py, px + 13, py - 11.5, "考核 assessment")
for j, g in enumerate(["期末占比", "案例占比", "平时占比"]):
    er.attr(ax_, ay_, ax_ + 8, ay_ + 3.2 - 3.2 * j, g, fs=8.5)

# --- OFFERING ---
OX, OY = 74, 47
er.entity(OX, OY, "教学班 OFFERING")
ring(er, OX, OY, [("班号 id", "key"), ("课号 code(FK)", ""), ("教师 teacher", ""),
                  ("教师评分 teacher_rating", ""), ("中签率 admit_rate", ""),
                  ("容量 capacity", ""), ("已选 enrolled", "")], rx=15, ry=8.5)

# --- SESSION 弱实体 ---
SX, SY = 78, 15
er.entity(SX, SY, "时段 SESSION", weak=True)
ring(er, SX, SY, [("星期 day", "partial"), ("起始节 start", "partial"),
                  ("结束节 end", ""), ("地点 location", "")], rx=13, ry=6)
er.diamond(76, 31, "安排", weak=True, w=7, h=3.2)
er.edge(OX, OY - 1.5, 75.5, 32.7)
er.edge(76, 29.3, SX, SY + 2.6)
er.ax.text(88, 25, "弱实体：主码 = (班号, day, start)", fontsize=8.5, color=RED, ha="center")

# --- TERM_CONFIG ---
TX, TY = 24, 12
er.entity(TX, TY, "学期配置 TERM_CONFIG", w=11)
tpos = ring(er, TX, TY, [("学期 term", "key"), ("专业 major", "key"), ("年级 grade", "key"),
                         ("学院 college", ""), ("公告 notice", ""), ("默认已修 completed", "multi")],
            rx=14, ry=7, start=100, span=255)
# graduation / earned 复合
gx, gy = er.attr(TX, TY, TX + 16, TY + 3.5, "毕业要求 graduation")
for j, m in enumerate(["必修学分", "专业选修学分", "通识学分"]):
    er.attr(gx, gy, gx + 10.5, gy + 4.5 - 4 * j, m, fs=8.5)
ex2, ey2 = er.attr(TX, TY, TX + 16, TY - 4, "已获学分 earned")
for j, m in enumerate(["必修", "专业选修", "通识"]):
    er.attr(ex2, ey2, ex2 + 9.5, ey2 + 3.2 - 3.2 * j, m, fs=8.5)
# requirements 多值复合
rx_, ry_ = er.attr(TX, TY, TX - 12, TY - 8, "模块学分要求 requirements", multi=True, fs=8.5)
er.attr(rx_, ry_, rx_ + 7.5, ry_ - 2.2, "模块 module", fs=8.5)
er.attr(rx_, ry_, rx_ + 19, ry_ - 2.2, "最低学分 min_credits", fs=8.5)

er.ax.text(70, 1.2, "图 1-a  参考库（seed.json）实体属性分图　——　双椭圆=多值属性，下划线=主码，虚线下划线=部分码",
           fontsize=11, ha="center", color="#555")
er.finish("/Users/kaisen/Documents/kimi/tasks/2026-11-23/20-17-55-6af837ac/er-1-参考库.png")

# ============ 图 2：学生档案与认证 ============
er = ER(20, 13, 100, 62)

# --- STUDENT + 复合档案 ---
DX, DY = 26, 47
er.entity(DX, DY, "学生 STUDENT")
ring(er, DX, DY, [("学号 id", "key"), ("版本号 revision", ""), ("创建时间 created_at", "")],
     rx=13, ry=6, start=100, span=140)
px, py = er.attr(DX, DY, DX - 3, DY - 10, "档案 profile / 草稿 draft（同构两份）", fs=9.5)
kids = ["姓名 name", "专业 major", "年级 grade", "目标 goal", "专注 focus",
        "挑战 challenge", "探索 exploration", "避开早八 avoid_early", "学分下限 min_credits", "学分上限 max_credits"]
for i, label in enumerate(kids):
    row, col = divmod(i, 5)
    er.attr(px, py, px - 20 + 10.5 * col, py - 5.5 - 4.5 * row, label, fs=8.5)
for j, label in enumerate(["已修 completed", "兴趣 interests", "锁定 locked", "排除 excluded", "禁排 blocked"]):
    er.attr(px, py, px - 21 + 11 * j, py - 14, label, multi=True, fs=8.5)

# --- MESSAGE ---
MX, MY = 62, 51
er.entity(MX, MY, "对话 MESSAGE", weak=True, w=8)
ring(er, MX, MY, [("角色 role", ""), ("内容 text", ""), ("时间 time", "partial")], rx=12, ry=5.5)

# --- FEEDBACK ---
FX, FY = 82, 47
er.entity(FX, FY, "反馈 FEEDBACK", w=8.5)
ring(er, FX, FY, [("反馈号 id", "key"), ("课号 course(FK)", ""), ("标签 tags", "multi"),
                  ("原因 reason", ""), ("方向 direction±1", ""), ("时间 time", ""), ("来源 source", "")],
     rx=11, ry=7)

# --- EVIDENCE ---
VX, VY = 64, 28
er.entity(VX, VY, "解析证据 EVIDENCE", weak=True, w=9)
ring(er, VX, VY, [("来源 source", ""), ("变更 changes", ""), ("时间 time", "partial"), ("提供方 provider", "")],
     rx=12, ry=5.5)

# --- OUTCOME_HISTORY ---
HX, HY = 84, 24
er.entity(HX, HY, "结果史 OUTCOME_HISTORY", weak=True, w=11)
ring(er, HX, HY, [("时间 time", "partial"), ("结果 outcome（预留）", "")], rx=13, ry=5.5)

# --- USERS / SESSIONS ---
UX, UY = 22, 12
er.entity(UX, UY, "用户 USERS")
ring(er, UX, UY, [("用户名 username", "key"), ("盐 salt", ""), ("口令散列 digest", ""),
                  ("绑定学号 student_id", "")], rx=13, ry=5.5)
GX, GY = 62, 10
er.entity(GX, GY, "会话 SESSIONS")
ring(er, GX, GY, [("令牌散列 token_hash", "key"), ("用户名 username(FK)", ""), ("过期时间 expires", "")],
     rx=13, ry=5.5)

er.ax.text(50, 3, "图 1-b  学生档案库（students/*.json）与认证库（auth.sqlite3）实体属性分图",
           fontsize=11, ha="center", color="#555")
er.finish("/Users/kaisen/Documents/kimi/tasks/2026-11-23/20-17-55-6af837ac/er-2-学生与认证.png")

# ============ 图 3：全局关系图 ============
er = ER(17, 10, 100, 60)
E, D, A = er.entity, er.diamond, er.attr
# 第一行：学期配置 —培养计划— 课程 —先修（自引用）
E(8, 54, "学期配置", w=9)
D(21, 54, "培养计划", w=10, h=4)
er.edge(12.5, 54, 16, 54); er.edge(26, 54, 30.5, 54)
er.ax.text(13.5, 55.4, "1", fontsize=10); er.ax.text(27.5, 55.4, "N", fontsize=10)
E(36, 54, "课程 COURSE", w=10)
A(21, 52, 11, 58, "模块 module", fs=8.5)
A(21, 52, 31, 58, "建议学期 suggest_term", fs=8.5)
D(55, 54, "先修", w=7, h=3.4)
er.edge(41, 55.5, 51.5, 55.2); er.edge(41, 52.5, 51.5, 52.8)
er.ax.text(46, 57, "M（主修课）", fontsize=9); er.ax.text(46, 50.6, "N（先修课）", fontsize=9)
# 课程 —开设— 教学班 —安排— 时段（弱实体）
D(36, 41, "开设", w=7, h=3.4)
er.edge(36, 52, 36, 42.7); er.edge(36, 39.3, 36, 36)
er.ax.text(37.2, 47, "1", fontsize=10); er.ax.text(37.2, 37, "N", fontsize=10)
E(36, 29, "教学班 OFFERING", w=11)
D(53, 29, "安排", weak=True, w=7, h=3.4)
er.edge(41.5, 29, 49.5, 29); er.edge(56.5, 29, 61.5, 29)
er.ax.text(44.5, 30.3, "1", fontsize=10); er.ax.text(59, 30.3, "N", fontsize=10)
E(67, 29, "时段 SESSION", weak=True, w=9)
# 学生 与其联系
E(8, 26, "学生 STUDENT", w=10)
D(16, 33, "反馈", w=7, h=3.4)
er.edge(10.5, 28, 13.5, 31.4); er.edge(18.5, 34.8, 31, 52)
er.ax.text(10.2, 30.4, "1", fontsize=10)
er.ax.text(26.5, 42.5, "N（对课程）", fontsize=9,
           bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
A(16, 31.3, 5.5, 44, "方向 direction", fs=8.5)
A(16, 31.3, 5.5, 40.5, "原因 reason", fs=8.5)
A(16, 31.3, 5.5, 37, "时间 time", fs=8.5)
A(16, 31.3, 5.5, 33.5, "来源 source", fs=8.5)
# 学生 —产生/留痕/回写— 三个弱实体
D(20, 19, "产生", w=6.4, h=3)
er.edge(12, 23.5, 17, 20.2); er.edge(23.2, 19.5, 29.5, 20)
er.ax.text(13.6, 22.6, "1", fontsize=10); er.ax.text(26.5, 21.3, "N", fontsize=10)
E(36, 20, "对话 MESSAGE", weak=True, w=9.5)
D(20, 10, "留痕", w=6.4, h=3)
er.edge(9, 23.5, 17.2, 11.4); er.edge(23.2, 10.2, 29.5, 11)
er.ax.text(8, 17, "1", fontsize=10); er.ax.text(26.5, 12.3, "N", fontsize=10)
E(36, 11, "解析证据 EVIDENCE", weak=True, w=12)
D(20, 2, "回写", w=6.4, h=3)
er.edge(6, 23.5, 17.2, 3.3); er.edge(23.2, 2, 27.5, 2)
er.ax.text(4.8, 12.5, "1", fontsize=10); er.ax.text(25.5, 3.4, "N", fontsize=10)
E(36, 2, "结果史 OUTCOME_HISTORY", weak=True, w=14)
# 认证（跨库逻辑联系用虚线）
E(84, 54, "用户 USERS", w=8.5)
E(84, 43, "会话 SESSIONS", w=9)
D(84, 48.5, "登录", w=6.4, h=3)
er.edge(84, 52, 84, 50); er.edge(84, 47, 84, 44.5)
er.ax.text(85.2, 51, "1", fontsize=10); er.ax.text(85.2, 45.5, "N", fontsize=10)
er.edge(79.8, 52.5, 13, 27.5, dash=True, color=RED)
er.ax.text(50, 40.5, "1:1 绑定（student_id，跨库逻辑外键）", fontsize=9, color=RED,
           bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=RED, lw=0.6))
er.ax.text(50, 58.7, "图 2  CoursePilot 全局 E-R 关系图（菱形=联系，双菱形/双矩形=弱实体及识别联系）",
           fontsize=13, weight="bold", ha="center")
er.finish("/Users/kaisen/Documents/kimi/tasks/2026-11-23/20-17-55-6af837ac/er-3-全局关系.png")
