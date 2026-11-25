# -*- coding: utf-8 -*-
"""CoursePilot BCNF 版陈氏 ER 图（对应 db/schema.sql 的 31 张表）"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, Polygon
import matplotlib.font_manager as fm
import math

_FONTS = "/Users/kaisen/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/fonts"
for f in ("NotoSansCJKsc-Regular.otf", "NotoSansCJKsc-Bold.otf"):
    fm.fontManager.addfont(f"{_FONTS}/{f}")
plt.rcParams["font.family"] = ["Noto Sans CJK SC"]

INK = "#1B1F24"; GOLD = "#B7950B"; RED = "#B03A2E"

def _ulen(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

class ER:
    def __init__(self, w_in, h_in, xlim, ylim):
        self.fig, self.ax = plt.subplots(figsize=(w_in, h_in))
        self.ax.set_xlim(0, xlim); self.ax.set_ylim(0, ylim)
        self.ax.axis("off"); self.xlim = xlim; self.ylim = ylim
        self.underlines = []

    def entity(self, x, y, name, weak=False, w=7.5, h=3.0, fs=12.5):
        if weak:
            self.ax.add_patch(Rectangle((x - w/2 - 0.5, y - h/2 - 0.5), w + 1, h + 1,
                                        fill=False, ec=INK, lw=1.2))
        self.ax.add_patch(Rectangle((x - w/2, y - h/2), w, h, fc="white", ec=INK, lw=1.4, zorder=3))
        self.ax.text(x, y, name, ha="center", va="center", fontsize=fs, weight="bold", zorder=4)

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
             fs=9.5, connect=True):
        u = _ulen(name)
        w = 0.62 * u + 2.2
        h = 1.7 + 0.12 * (fs - 9.5)
        if multi:
            self.ax.add_patch(Ellipse((x, y), w * 1.16, h * 1.32, fill=False, ec=INK, lw=1.0, zorder=3))
        self.ax.add_patch(Ellipse((x, y), w, h, fc="white", ec=INK, lw=1.1, zorder=3))
        t = self.ax.text(x, y, name, ha="center", va="center", fontsize=fs, zorder=4)
        if connect:
            self.edge(ex, ey, x, y)
        if key or partial:
            self.underlines.append((t, partial))
        return x, y

    def finish(self, path, title=None):
        if title:
            self.ax.text(self.xlim / 2, self.ylim - 1.2, title, fontsize=15,
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

def ring(er, ex, ey, names, rx, ry, start=90, span=360):
    n = len(names)
    for i, (label, kind) in enumerate(names):
        ang = math.radians(start - span * i / n)
        er.attr(ex, ey, ex + rx * math.cos(ang), ey + ry * math.sin(ang), label,
                key=(kind == "key"), multi=(kind == "multi"), partial=(kind == "partial"))

OUT = "/Users/kaisen/Documents/kimi/tasks/2026-11-23/20-17-55-6af837ac"

# ============ 图 1-a（BCNF）：参考库 ============
er = ER(20, 13, 100, 62)

# COURSE（画像已拆出）
CX, CY = 16, 45
er.entity(CX, CY, "课程 COURSE")
ring(er, CX, CY, [("课号 code", "key"), ("名称 name", ""), ("学分 credits", ""), ("类别 category", "")],
     rx=11, ry=7.5)
# TAG 弱实体（多值属性拆表）
er.entity(4, 30, "标签 TAG", weak=True, w=6, fs=10)
er.attr(4, 30, 4, 25.5, "标签 tag", partial=True, fs=8.5)
er.diamond(10, 36.5, "标注", weak=True, w=6.4, h=3)
er.edge(CX - 3, CY - 1.5, 11.5, 37.4); er.edge(8.6, 35.2, 6, 31.6)
# 先修（N:M 自引用联系）
er.diamond(3, 52, "先修", w=6.4, h=3)
er.edge(CX - 3.75, CY + 2, 5, 53.3); er.edge(CX - 5.5, CY + 0.5, 4.2, 50.7)
er.ax.text(6.5, 55.3, "M 主修", fontsize=8); er.ax.text(0.2, 48.6, "N 先修", fontsize=8)

# COURSE_PROFILE（1:1 拆出）
PX, PY = 46, 51
er.entity(PX, PY, "课程画像 COURSE_PROFILE", w=15)
er.diamond(31, 49, "拥有", w=6.4, h=3)
er.edge(CX + 3.75, CY + 1, 28, 48.4); er.edge(34, 49.5, 38.5, 50.5)
er.ax.text(25, 50.2, "1", fontsize=9.5); er.ax.text(36.5, 51.6, "1", fontsize=9.5)
ring(er, PX, PY, [("课号 code", "key"), ("周学时 weekly_hours", ""), ("难度 difficulty", ""),
                  ("给分 grading", ""), ("风格 style", ""), ("点名 attendance", ""),
                  ("样本量 sample_size", ""), ("置信度 confidence", ""), ("摘要 summary", "")],
     rx=14, ry=6.5)
# ASSESSMENT 弱实体
AX, AY = 46, 30
er.entity(AX, AY, "考核项 ASSESSMENT", weak=True, w=12, fs=10.5)
er.diamond(PX, 41.5, "组成", weak=True, w=6.4, h=3)
er.edge(PX, PY - 1.5, PX, 43); er.edge(PX, 40, AX, AY + 2)
er.attr(AX, AY, AX - 11, AY, "组件 component", partial=True, fs=8.5)
er.attr(AX, AY, AX + 11, AY, "权重 weight", fs=8.5)

# TEACHER（传递依赖拆出） / OFFERING / SESSION
TX2, TY2 = 84, 52
er.entity(TX2, TY2, "教师 TEACHER", w=9)
er.attr(TX2, TY2, TX2 - 10, TY2 + 5, "姓名 name", key=True)
er.attr(TX2, TY2, TX2 + 10, TY2 + 5, "评分 rating")
OX, OY = 84, 36
er.entity(OX, OY, "教学班 OFFERING", w=10)
er.diamond(TX2, 44, "任教", w=6.4, h=3)
er.edge(TX2, TY2 - 1.5, TX2, 45.7); er.edge(TX2, 42.3, OX, OY + 1.5)
er.ax.text(TX2 + 1.2, 47.5, "1", fontsize=9.5); er.ax.text(OX + 1.2, 39.8, "N", fontsize=9.5)
ring(er, OX, OY, [("班号 id", "key"), ("课号 code(FK)", ""), ("中签率 admit_rate", ""),
                  ("容量 capacity", ""), ("已选 enrolled", "")], rx=13, ry=5.5, start=200, span=290)
SX, SY = 84, 16
er.entity(SX, SY, "时段 SESSION", weak=True)
er.diamond(OX, 26, "安排", weak=True, w=6.4, h=3)
er.edge(OX, OY - 1.5, OX, 27.7); er.edge(OX, 24.3, SX, SY + 2)
ring(er, SX, SY, [("星期 day", "partial"), ("起始节 start", "partial"),
                  ("结束节 end", ""), ("地点 location", "")], rx=11, ry=5, start=200, span=290)

# MAJOR / TERM_CONFIG / MODULE_REQ
MX, MY = 8, 8
er.entity(MX, MY, "专业 MAJOR", w=8)
er.attr(MX, MY, MX - 7, MY + 5, "专业名 name", key=True, fs=8.5)
er.attr(MX, MY, MX - 7, MY - 4.5, "学院 college", fs=8.5)
EX, EY = 34, 8
er.entity(EX, EY, "学期配置 TERM_CONFIG", w=13)
er.diamond(21, 8, "属于", w=6.4, h=3)
er.edge(MX + 4, MY, 17.8, 8); er.edge(24.2, 8, EX - 6.5, 8)
er.ax.text(14, 9.2, "1", fontsize=9.5); er.ax.text(27.5, 9.2, "N", fontsize=9.5)
er.attr(EX, EY, EX - 4, EY + 5.5, "学期 term", key=True, fs=8.5)
er.attr(EX, EY, EX + 4.5, EY + 5.5, "专业 major(FK)", key=True, fs=8.5)
er.attr(EX, EY, EX + 12, EY + 2, "年级 grade", key=True, fs=8.5)
er.attr(EX, EY, EX + 12, EY - 2, "公告 notice", fs=8.5)
RX, RY = 62, 8
er.entity(RX, RY, "模块要求 MODULE_REQ", weak=True, w=14, fs=10)
er.diamond(51.5, 8, "要求", weak=True, w=6.4, h=3)
er.edge(EX + 6.5, EY, 48.3, 8); er.edge(54.7, 8, RX - 7, 8)
er.attr(RX, RY, RX - 3, RY + 5.5, "模块 module", partial=True, fs=8.5)
er.attr(RX, RY, RX + 9, RY + 5.5, "最低学分 min_credits", fs=8.5)
er.ax.text(RX, RY - 4.5, "（毕业要求 / 已获学分 / 默认已修 三张从表同构，从略）", fontsize=8, color="#555", ha="center")

er.ax.text(50, 1.2, "图 1-a′  参考库实体属性分图（BCNF）—— 下划线=主码，虚线下划线=部分码，双框=弱实体",
           fontsize=11, ha="center", color="#555")
er.finish(f"{OUT}/er-bcnf-1-参考库.png")

# ============ 图 1-b（BCNF）：学生与认证 ============
er = ER(20, 13, 100, 62)

DX, DY = 22, 44
er.entity(DX, DY, "学生 STUDENT", w=10)
ring(er, DX, DY, [("学号 id", "key"), ("姓名 name", ""), ("专业 major(FK)", ""),
                  ("年级 grade", ""), ("目标 goal", ""), ("版本号 revision", ""), ("创建时间 created_at", ""),
                  ("专注 focus", ""), ("挑战 challenge", ""), ("探索 exploration", ""),
                  ("避开早八 avoid_early", ""), ("学分下限 min_credits", ""), ("学分上限 max_credits", "")],
     rx=14, ry=8.5)

# 多值从表（弱实体组）
for i, (name, attr) in enumerate([("已修 COMPLETED", "课号 code"), ("兴趣 INTEREST", "标签 tag"),
                                  ("锁定 LOCKED", "值 value"), ("排除 EXCLUDED", "值 value"),
                                  ("禁排 BLOCKED", "值 value"), ("加权 AFFINITY", "课号+权重")]):
    y = 56 - 5.4 * i
    er.entity(56, y, name, weak=True, w=13, h=2.4, fs=9)
    er.attr(56, y, 70, y, attr, partial=("权重" not in attr), fs=8)
er.diamond(41, 44, "包含", weak=True, w=6.4, h=3)
er.edge(DX + 5, DY, 38, 43.8)
for i in range(6):
    y = 56 - 5.4 * i
    er.edge(43.8, 44.5, 49.5, y)
er.ax.text(56, 26, "多值属性各拆一张从表（4NF），部分码 = 值本身", fontsize=8, color="#555", ha="center")

# DRAFT 1:1
RX2, RY2 = 10, 18
er.entity(RX2, RY2, "草稿 DRAFT", w=9)
er.diamond(13, 29, "暂存", w=6.4, h=3)
er.edge(DX - 6, DY - 1.5, 14.2, 30.5); er.edge(12, 27.5, RX2 + 2, RY2 + 1.5)
er.ax.text(11.5, 32.5, "1", fontsize=9.5); er.ax.text(14.5, 25.8, "0..1", fontsize=9.5)
er.ax.text(RX2, RY2 - 3.6, "单值属性同档案；多值进 DRAFT_ITEM(kind, value)", fontsize=7.5, color="#555", ha="center")

# MESSAGE / FEEDBACK / EVIDENCE / OUTCOME
MX3, MY3 = 40, 12
er.entity(MX3, MY3, "对话 MESSAGE", weak=True, w=10)
er.attr(MX3, MY3, MX3 - 9, MY3 + 4.5, "时间 time", partial=True, fs=8.5)
er.attr(MX3, MY3, MX3 + 1, MY3 + 5.5, "序号 seq", partial=True, fs=8.5)
er.attr(MX3, MY3, MX3 + 10, MY3 + 3.5, "角色 role", fs=8.5)
er.attr(MX3, MY3, MX3 + 10, MY3 - 3.5, "内容 text", fs=8.5)

FX, FY = 84, 46
er.entity(FX, FY, "反馈 FEEDBACK", w=10)
ring(er, FX, FY, [("反馈号 id", "key"), ("学号 student_id(FK)", ""), ("课号 course(FK)", ""),
                  ("原因 reason", ""), ("方向 direction", ""), ("时间 time", ""), ("来源 source", "")],
     rx=12, ry=7)
er.ax.text(FX, FY - 9.5, "注：tags 快照列已删除（course → tags 传递依赖）", fontsize=8, color=RED, ha="center")

VX, VY = 74, 24
er.entity(VX, VY, "解析证据 EVIDENCE", weak=True, w=12, fs=10)
er.attr(VX, VY, VX - 11, VY + 5, "时间 time", partial=True, fs=8.5)
er.attr(VX, VY, VX - 1, VY + 6, "来源 source", fs=8.5)
er.attr(VX, VY, VX + 10, VY - 4.5, "提供方 provider", fs=8.5)
er.entity(VX + 17, VY, "变更 CHANGE", weak=True, w=9, fs=10)
er.diamond(VX + 8.5, VY, "含", weak=True, w=4.6, h=2.6)
er.edge(VX + 6, VY, VX + 6.4, VY); er.edge(VX + 11, VY, VX + 12.5, VY)
er.attr(VX + 17, VY, VX + 17, VY - 4.2, "序号 seq", partial=True, fs=8)
er.attr(VX + 17, VY, VX + 17, VY + 4.2, "内容 change", fs=8)

HX, HY = 28, 4.5
er.entity(HX, HY, "结果史 OUTCOME", weak=True, w=11, fs=10)
er.attr(HX, HY, HX - 8, HY + 4.5, "时间 time", partial=True, fs=8.5)
er.attr(HX, HY, HX + 11, HY + 4.5, "内容 payload", fs=8.5)

UX, UY = 84, 6
er.entity(UX, UY, "用户 USERS")
er.attr(UX, UY, UX - 6, UY + 5, "用户名 username", key=True, fs=8.5)
er.attr(UX, UY, UX + 9, UY + 4, "盐 salt", fs=8.5)
er.attr(UX, UY, UX + 9, UY - 4, "口令散列 digest", fs=8.5)
er.attr(UX, UY, UX - 7, UY - 4.5, "学号 student_id(UK,FK)", fs=8.5)
GX, GY = 60, 12
er.entity(GX, GY, "会话 SESSIONS", w=10)
er.attr(GX, GY, GX - 6, GY + 5.5, "令牌散列 token_hash", key=True, fs=8.5)
er.attr(GX, GY, GX + 2, GY + 6, "用户名 username(FK)", fs=8.5)
er.attr(GX, GY, GX + 11, GY - 3.5, "过期时间 expires", fs=8.5)

er.ax.text(50, 1.2, "图 1-b′  学生档案与认证实体属性分图（BCNF）",
           fontsize=11, ha="center", color="#555")
er.finish(f"{OUT}/er-bcnf-2-学生与认证.png")

# ============ 图 2（BCNF）：全局关系图 ============
er = ER(17, 10, 100, 60)
E, D = er.entity, er.diamond

# 第一行：MAJOR — TERM_CONFIG —培养计划— COURSE —先修（自）
E(8, 54, "专业 MAJOR", w=8.5, fs=11)
D(19, 54, "属于", w=6, h=3.2)
er.edge(12.2, 54, 16, 54); er.edge(22, 54, 25.5, 54)
er.ax.text(13.5, 55.3, "1", fontsize=9.5); er.ax.text(23.5, 55.3, "N", fontsize=9.5)
E(31, 54, "学期配置", w=9, fs=11)
D(42, 54, "培养计划", w=9, h=3.6)
er.edge(35.5, 54, 37.5, 54); er.edge(46.5, 54, 48.5, 54)
er.ax.text(36.3, 55.3, "1", fontsize=9.5); er.ax.text(47.3, 55.3, "N", fontsize=9.5)
er.attr(42, 52.2, 36, 49.6, "建议学期 suggest_term", fs=8.5)
E(54, 54, "课程 COURSE", w=10, fs=11)
D(73, 54, "先修", w=6.4, h=3.2)
er.edge(59, 55.5, 69.8, 55); er.edge(59, 52.5, 69.8, 53)
er.ax.text(63, 56.8, "M 主修", fontsize=8.5); er.ax.text(63, 50.9, "N 先修", fontsize=8.5)

# 第二行：COURSE —拥有— PROFILE —组成— ASSESSMENT；COURSE —开设— OFFERING —任教— TEACHER；OFFERING—安排—SESSION
D(54, 42, "拥有", w=6, h=3.2)
er.edge(54, 52, 54, 43.6); er.edge(54, 40.4, 54, 38)
er.ax.text(55.2, 46.5, "1", fontsize=9.5); er.ax.text(55.2, 39.2, "1", fontsize=9.5)
E(54, 34, "课程画像", w=9, fs=11)
D(54, 24, "组成", weak=True, w=6, h=3.2)
er.edge(54, 32, 54, 25.6); er.edge(54, 22.4, 54, 20)
er.ax.text(55.2, 29.5, "1", fontsize=9.5); er.ax.text(55.2, 21.2, "N", fontsize=9.5)
E(54, 16, "考核项 ASSESSMENT", weak=True, w=13, fs=10.5)

D(70, 42, "开设", w=6, h=3.2)
er.edge(58, 51.5, 67.5, 43.3)
er.ax.text(61, 48.6, "1", fontsize=9.5)
E(78, 34, "教学班 OFFERING", w=11, fs=11)
er.edge(72.5, 40.8, 74.5, 35.5)
er.ax.text(75.5, 38.6, "N", fontsize=9.5)
E(94, 46, "教师 TEACHER", w=9, fs=11)
D(90, 40, "任教", w=6, h=3.2)
er.edge(94, 44, 91.8, 41.3); er.edge(88, 38.8, 83.5, 35.2)
er.ax.text(94.8, 42.2, "1", fontsize=9.5); er.ax.text(87.5, 36, "N", fontsize=9.5)
D(78, 24, "安排", weak=True, w=6, h=3.2)
er.edge(78, 32, 78, 25.6); er.edge(78, 22.4, 78, 20)
er.ax.text(79.2, 29.5, "1", fontsize=9.5); er.ax.text(79.2, 21.2, "N", fontsize=9.5)
E(78, 16, "时段 SESSION", weak=True, w=9, fs=11)
E(41, 41.5, "标签 TAG", weak=True, w=7, fs=10.5)
D(47.5, 47.5, "标注", weak=True, w=5.4, h=2.8)
er.edge(52, 52.5, 48.7, 48.7); er.edge(46, 46.2, 42.8, 43)
er.ax.text(51.5, 50.3, "1", fontsize=9); er.ax.text(44, 43.6, "N", fontsize=9)

# 学生域
E(10, 34, "学生 STUDENT", w=10, fs=11)
D(26, 36, "反馈", w=6.4, h=3.2)
er.edge(13.5, 36.5, 23, 36.8); er.edge(29.2, 37, 49.5, 52.2)
er.ax.text(16, 38.3, "1", fontsize=9.5); er.ax.text(33.5, 45.5, "N（对课程）", fontsize=9)
er.ax.text(26, 32.3, "属性：原因/方向/时间/来源", fontsize=8, color="#555", ha="center")
D(26, 27, "包含", weak=True, w=6.4, h=3.2)
er.edge(13, 31.8, 23, 28.2); er.edge(29.2, 26.6, 33, 26)
E(40, 26, "多值从表×6", weak=True, w=11, fs=10.5)
er.ax.text(40, 23.2, "已修/兴趣/锁定/排除/禁排/加权", fontsize=7.5, color="#555", ha="center")
D(26, 18, "暂存", w=6, h=3)
er.edge(10.5, 32, 23.5, 19.3); er.edge(28.8, 17.5, 31.5, 17)
er.ax.text(15, 25.3, "1", fontsize=9.5); er.ax.text(30.5, 19, "0..1", fontsize=9)
E(38, 17, "草稿 DRAFT", w=9, fs=11)
D(26, 10, "产生/留痕/回写", w=13, h=3.4)
er.edge(9.5, 32, 21, 11.4); er.edge(32.5, 10, 35.5, 10)
E(43, 10, "MESSAGE / EVIDENCE / OUTCOME", weak=True, w=22, fs=10)

# 认证
E(90, 8, "用户 USERS", w=8.5, fs=11)
E(90, 0.5, "会话 SESSIONS", w=9, fs=10.5)
D(90, 4.2, "登录", w=5.6, h=2.8)
er.edge(90, 6, 90, 5.6); er.edge(90, 2.8, 90, 2)
er.ax.text(91.2, 5.6, "1", fontsize=9); er.ax.text(91.2, 2.8, "N", fontsize=9)
er.ax.plot([85.7, 6, 6], [8, 8, 32], ls="--", color=RED, lw=1.1, zorder=1)
er.edge(6, 34, 5, 34, dash=True, color=RED)
er.ax.text(46, 6.2, "1:1 绑定（student_id）", fontsize=8.5, color=RED,
           bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=RED, lw=0.6))

er.ax.text(50, 59, "图 2′  CoursePilot 全局 E-R 关系图（BCNF 版）",
           fontsize=13, weight="bold", ha="center")
er.finish(f"{OUT}/er-bcnf-3-全局关系.png")
