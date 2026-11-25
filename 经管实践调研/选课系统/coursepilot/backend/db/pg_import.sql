SET client_encoding = 'UTF8';
BEGIN;
-- CoursePilot BCNF 关系模式（SQLite 方言）
-- 设计原则：
--   1. 所有多值属性拆为独立从表（达到 1NF/4NF）
--   2. 消除传递依赖：TEACHER 独立（teacher → teacher_rating）；
--      PLAN_ITEM 删除 module（由 COURSE.category 决定）；MAJOR 独立（major → college）
--   3. 每个非平凡函数依赖的决定因素均为超码 → BCNF
--   4. FEEDBACK 不存 tags（由 course 决定，快照冗余，消除传递依赖）



-- ========== 参考数据域（原 seed.json） ==========

CREATE TABLE major (
    name    TEXT PRIMARY KEY,
    college TEXT NOT NULL
);

CREATE TABLE term_config (
    term   TEXT NOT NULL,
    major  TEXT NOT NULL REFERENCES major(name),
    grade  INTEGER NOT NULL,
    notice TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (term, major, grade)
);

CREATE TABLE module_req (
    term        TEXT NOT NULL,
    major       TEXT NOT NULL,
    grade       INTEGER NOT NULL,
    module      TEXT NOT NULL,
    min_credits REAL NOT NULL,
    PRIMARY KEY (term, major, grade, module),
    FOREIGN KEY (term, major, grade) REFERENCES term_config(term, major, grade)
);

CREATE TABLE graduation_req (
    term    TEXT NOT NULL,
    major   TEXT NOT NULL,
    grade   INTEGER NOT NULL,
    module  TEXT NOT NULL,
    credits REAL NOT NULL,
    PRIMARY KEY (term, major, grade, module),
    FOREIGN KEY (term, major, grade) REFERENCES term_config(term, major, grade)
);

CREATE TABLE earned_default (
    term    TEXT NOT NULL,
    major   TEXT NOT NULL,
    grade   INTEGER NOT NULL,
    module  TEXT NOT NULL,
    credits REAL NOT NULL,
    PRIMARY KEY (term, major, grade, module),
    FOREIGN KEY (term, major, grade) REFERENCES term_config(term, major, grade)
);

CREATE TABLE default_completed (
    term TEXT NOT NULL,
    major TEXT NOT NULL,
    grade INTEGER NOT NULL,
    code TEXT NOT NULL,
    PRIMARY KEY (term, major, grade, code),
    FOREIGN KEY (term, major, grade) REFERENCES term_config(term, major, grade)
);

CREATE TABLE course (
    code     TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    credits  REAL NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE course_tag (
    code TEXT NOT NULL REFERENCES course(code),
    tag  TEXT NOT NULL,
    PRIMARY KEY (code, tag)
);

CREATE TABLE prereq (
    code        TEXT NOT NULL REFERENCES course(code),
    -- prereq_code 不加外键：先修课可能不在本学期开课列表中（如 MATH1101 等低年级课）
    prereq_code TEXT NOT NULL,
    PRIMARY KEY (code, prereq_code)
);

-- 课程画像：与教务事实分表（来源、更新频率、置信度均不同）
CREATE TABLE course_profile (
    code         TEXT PRIMARY KEY REFERENCES course(code),
    weekly_hours REAL,
    difficulty   REAL,
    grading      REAL,
    style        TEXT,
    attendance   INTEGER,          -- 0/1
    sample_size  INTEGER,
    confidence   REAL,
    summary      TEXT
);

CREATE TABLE assessment (
    code      TEXT NOT NULL REFERENCES course(code),
    component TEXT NOT NULL,
    weight    REAL NOT NULL,
    PRIMARY KEY (code, component)
);

CREATE TABLE teacher (
    name   TEXT PRIMARY KEY,
    rating REAL
);

CREATE TABLE offering (
    id         TEXT PRIMARY KEY,
    code       TEXT NOT NULL REFERENCES course(code),
    teacher    TEXT NOT NULL REFERENCES teacher(name),
    admit_rate REAL,
    capacity   INTEGER,
    enrolled   INTEGER
);

-- 弱实体：主码含依赖实体的码
CREATE TABLE session (
    offering_id TEXT NOT NULL REFERENCES offering(id),
    day         INTEGER NOT NULL,
    start       INTEGER NOT NULL,
    "end"      INTEGER NOT NULL,
    location    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (offering_id, day, start)
);

-- module 列已删除：code → category 由 COURSE 表决定
CREATE TABLE plan_item (
    term         TEXT NOT NULL,
    major        TEXT NOT NULL,
    grade        INTEGER NOT NULL,
    code         TEXT NOT NULL REFERENCES course(code),
    suggest_term INTEGER,
    PRIMARY KEY (term, major, grade, code),
    FOREIGN KEY (term, major, grade) REFERENCES term_config(term, major, grade)
);

-- ========== 学生档案域（原 students/*.json） ==========

CREATE TABLE student (
    id            TEXT PRIMARY KEY,          -- UUID
    revision      INTEGER NOT NULL DEFAULT 0, -- 乐观锁
    created_at    TEXT,
    name          TEXT,
    major         TEXT REFERENCES major(name),
    grade         INTEGER,
    goal          TEXT,
    focus         REAL,
    challenge     REAL,
    exploration   REAL,
    avoid_early   INTEGER,                   -- 0/1
    min_credits   REAL,
    max_credits   REAL
);

-- 正式档案的多值属性（每个一张二列表 → 4NF）
CREATE TABLE student_completed (
    student_id TEXT NOT NULL REFERENCES student(id),
    code       TEXT NOT NULL,
    PRIMARY KEY (student_id, code)
);
CREATE TABLE student_interest (
    student_id TEXT NOT NULL REFERENCES student(id),
    tag        TEXT NOT NULL,
    PRIMARY KEY (student_id, tag)
);
CREATE TABLE student_locked (
    student_id TEXT NOT NULL REFERENCES student(id),
    value      TEXT NOT NULL,
    PRIMARY KEY (student_id, value)
);
CREATE TABLE student_excluded (
    student_id TEXT NOT NULL REFERENCES student(id),
    value      TEXT NOT NULL,
    PRIMARY KEY (student_id, value)
);
CREATE TABLE student_blocked (
    student_id TEXT NOT NULL REFERENCES student(id),
    value      TEXT NOT NULL,
    PRIMARY KEY (student_id, value)
);
CREATE TABLE student_affinity (
    student_id TEXT NOT NULL REFERENCES student(id),
    course     TEXT NOT NULL REFERENCES course(code),
    weight     REAL NOT NULL,
    PRIMARY KEY (student_id, course)
);

-- 草稿档案：0..1，单值属性一表，多值属性用 kind 区分（草稿是暂存工作副本）
CREATE TABLE draft (
    student_id  TEXT PRIMARY KEY REFERENCES student(id),
    name        TEXT,
    major       TEXT,
    grade       INTEGER,
    goal        TEXT,
    focus       REAL,
    challenge   REAL,
    exploration REAL,
    avoid_early INTEGER,
    min_credits REAL,
    max_credits REAL
);
CREATE TABLE draft_item (
    student_id TEXT NOT NULL REFERENCES draft(student_id),
    kind       TEXT NOT NULL CHECK (kind IN ('completed','interests','locked','excluded','blocked')),
    value      TEXT NOT NULL,
    PRIMARY KEY (student_id, kind, value)
);

-- 弱实体：消息按时间戳可能同刻成对（问与答），主码加序号
CREATE TABLE message (
    student_id TEXT NOT NULL REFERENCES student(id),
    time       TEXT NOT NULL,
    seq        INTEGER NOT NULL DEFAULT 0,
    role       TEXT NOT NULL,
    text       TEXT NOT NULL,
    PRIMARY KEY (student_id, time, seq)
);

-- tags 列已删除：由 course → COURSE_TAG 决定，不存快照
CREATE TABLE feedback (
    id         TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES student(id),
    course     TEXT NOT NULL REFERENCES course(code),
    reason     TEXT,
    direction  INTEGER CHECK (direction IN (-1, 1)),
    time       TEXT NOT NULL,
    source     TEXT
);

CREATE TABLE evidence (
    student_id TEXT NOT NULL REFERENCES student(id),
    time       TEXT NOT NULL,
    source     TEXT,
    provider   TEXT,
    PRIMARY KEY (student_id, time)
);
CREATE TABLE evidence_change (
    student_id TEXT NOT NULL,
    time       TEXT NOT NULL,
    seq        INTEGER NOT NULL,
    change     TEXT NOT NULL,
    PRIMARY KEY (student_id, time, seq),
    FOREIGN KEY (student_id, time) REFERENCES evidence(student_id, time)
);

-- 预留：选课结果回写（闭环），结构待业务定型后细化
CREATE TABLE outcome_history (
    student_id TEXT NOT NULL REFERENCES student(id),
    time       TEXT NOT NULL,
    payload    TEXT,
    PRIMARY KEY (student_id, time)
);

-- ========== 认证域（原 auth.sqlite3） ==========

CREATE TABLE users (
    username   TEXT PRIMARY KEY,
    salt       TEXT NOT NULL,
    digest     TEXT NOT NULL,
    student_id TEXT NOT NULL UNIQUE REFERENCES student(id)
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    username   TEXT NOT NULL REFERENCES users(username),
    expires    REAL NOT NULL
);

INSERT INTO major (name, college) VALUES ('金融学', '安泰经济与管理学院');
INSERT INTO term_config (term, major, grade, notice) VALUES ('2026-2027-1', '金融学', 2024, '演示数据：课程信息与教师评价均为示例，不代表上海交通大学安泰经管学院真实开课情况。');
INSERT INTO module_req (term, major, grade, module, min_credits) VALUES ('2026-2027-1', '金融学', 2024, '必修', 12.0);
INSERT INTO module_req (term, major, grade, module, min_credits) VALUES ('2026-2027-1', '金融学', 2024, '专业选修', 6.0);
INSERT INTO module_req (term, major, grade, module, min_credits) VALUES ('2026-2027-1', '金融学', 2024, '通识', 2.0);
INSERT INTO graduation_req (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '必修', 78.0);
INSERT INTO graduation_req (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '专业选修', 26.0);
INSERT INTO graduation_req (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '通识', 22.0);
INSERT INTO earned_default (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '必修', 61.0);
INSERT INTO earned_default (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '专业选修', 9.0);
INSERT INTO earned_default (term, major, grade, module, credits) VALUES ('2026-2027-1', '金融学', 2024, '通识', 16.0);
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'MATH1101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'MATH1201');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'MATH2201');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'ECON1101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'ECON2101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'ECON2102');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'ACC2101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'STAT2101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'MGT1101');
INSERT INTO default_completed (term, major, grade, code) VALUES ('2026-2027-1', '金融学', 2024, 'PE1001');
INSERT INTO course (code, name, credits, category) VALUES ('FI3101', '公司金融', 3.0, '必修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3102', '投资学', 3.0, '必修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3103', '计量经济学', 3.0, '必修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3104', '货币银行学', 3.0, '必修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3201', '金融工程', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3202', '固定收益证券', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3203', '国际金融', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3204', '行为金融学', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3205', '金融科技与区块链', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3206', '公司估值与并购', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3207', '衍生品定价', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('FI3208', '商业银行经营管理', 3.0, '专业选修');
INSERT INTO course (code, name, credits, category) VALUES ('GE2201', '经济思想史', 2.0, '通识');
INSERT INTO course (code, name, credits, category) VALUES ('GE2202', '商业伦理', 2.0, '通识');
INSERT INTO course (code, name, credits, category) VALUES ('GE2203', '心理学与决策', 2.0, '通识');
INSERT INTO course (code, name, credits, category) VALUES ('GE2204', '学术英语写作', 2.0, '通识');
INSERT INTO course_tag (code, tag) VALUES ('FI3101', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3101', '估值');
INSERT INTO course_tag (code, tag) VALUES ('FI3101', '核心');
INSERT INTO course_tag (code, tag) VALUES ('FI3102', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3102', '量化');
INSERT INTO course_tag (code, tag) VALUES ('FI3102', '核心');
INSERT INTO course_tag (code, tag) VALUES ('FI3103', '计量');
INSERT INTO course_tag (code, tag) VALUES ('FI3103', '数学');
INSERT INTO course_tag (code, tag) VALUES ('FI3103', '实证');
INSERT INTO course_tag (code, tag) VALUES ('FI3104', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3104', '宏观');
INSERT INTO course_tag (code, tag) VALUES ('FI3104', '理论');
INSERT INTO course_tag (code, tag) VALUES ('FI3201', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3201', '数学');
INSERT INTO course_tag (code, tag) VALUES ('FI3201', '进阶');
INSERT INTO course_tag (code, tag) VALUES ('FI3201', '热门');
INSERT INTO course_tag (code, tag) VALUES ('FI3202', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3202', '量化');
INSERT INTO course_tag (code, tag) VALUES ('FI3202', '实务');
INSERT INTO course_tag (code, tag) VALUES ('FI3203', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3203', '宏观');
INSERT INTO course_tag (code, tag) VALUES ('FI3203', '国际');
INSERT INTO course_tag (code, tag) VALUES ('FI3204', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3204', '行为');
INSERT INTO course_tag (code, tag) VALUES ('FI3204', '热门');
INSERT INTO course_tag (code, tag) VALUES ('FI3205', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3205', '编程');
INSERT INTO course_tag (code, tag) VALUES ('FI3205', '前沿');
INSERT INTO course_tag (code, tag) VALUES ('FI3206', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3206', '估值');
INSERT INTO course_tag (code, tag) VALUES ('FI3206', '实务');
INSERT INTO course_tag (code, tag) VALUES ('FI3206', '热门');
INSERT INTO course_tag (code, tag) VALUES ('FI3207', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3207', '数学');
INSERT INTO course_tag (code, tag) VALUES ('FI3207', '进阶');
INSERT INTO course_tag (code, tag) VALUES ('FI3208', '金融');
INSERT INTO course_tag (code, tag) VALUES ('FI3208', '实务');
INSERT INTO course_tag (code, tag) VALUES ('FI3208', '银行');
INSERT INTO course_tag (code, tag) VALUES ('GE2201', '人文');
INSERT INTO course_tag (code, tag) VALUES ('GE2201', '经济');
INSERT INTO course_tag (code, tag) VALUES ('GE2201', '通识');
INSERT INTO course_tag (code, tag) VALUES ('GE2202', '人文');
INSERT INTO course_tag (code, tag) VALUES ('GE2202', '伦理');
INSERT INTO course_tag (code, tag) VALUES ('GE2202', '通识');
INSERT INTO course_tag (code, tag) VALUES ('GE2203', '人文');
INSERT INTO course_tag (code, tag) VALUES ('GE2203', '决策');
INSERT INTO course_tag (code, tag) VALUES ('GE2203', '通识');
INSERT INTO course_tag (code, tag) VALUES ('GE2203', '热门');
INSERT INTO course_tag (code, tag) VALUES ('GE2204', '语言');
INSERT INTO course_tag (code, tag) VALUES ('GE2204', '实用');
INSERT INTO course_tag (code, tag) VALUES ('GE2204', '通识');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3101', 'ACC2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3101', 'ECON1101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3102', 'ECON2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3102', 'STAT2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3103', 'STAT2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3103', 'MATH2201');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3104', 'ECON2102');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3201', 'STAT2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3201', 'MATH2201');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3202', 'STAT2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3203', 'ECON2102');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3204', 'ECON2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3205', 'STAT2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3206', 'ACC2101');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3207', 'MATH2201');
INSERT INTO prereq (code, prereq_code) VALUES ('FI3208', 'ECON2102');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3101', 7.0, 3.6, 3.8, '板书 + 案例', 1, 214, 0.91, '从资本预算讲到资本结构与股利政策，三次哈佛式案例讨论，期末考试计算量大。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3102', 8.0, 3.9, 3.6, '推导 + 实证', 0, 232, 0.9, '有效前沿、CAPM、因子模型一条线讲下来，最后用真实行情做一次组合回测。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3103', 9.0, 4.2, 3.5, '推导 + 代码', 1, 196, 0.88, '从 OLS 推导到面板数据与工具变量，作业用 Stata 或 R 复现实证论文。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3104', 5.0, 2.9, 4.2, 'PPT 串讲', 1, 258, 0.89, '以中国货币政策实践为主线，讲利率、汇率与银行体系，背诵内容偏多。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3201', 8.0, 4.3, 3.9, '推导 + 代码', 0, 148, 0.83, '期权定价、希腊字母、结构化产品设计，项目是用 Python 给一个雪球产品定价。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3202', 7.0, 3.7, 4.0, '案例 + Excel', 0, 132, 0.8, '久期、凸性、信用利差，用 Excel 做债券组合的利率风险度量，实务感强。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3203', 5.0, 3.0, 4.4, '案例讲授', 0, 176, 0.82, '汇率决定、国际收支、货币危机，讲课时事结合多，考试以简答与案例分析为主。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3204', 4.0, 2.6, 4.6, '论文研讨', 1, 164, 0.78, '以经典行为金融论文为主线，课堂讨论多，给分宽松，但要做两次文献汇报。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3205', 7.0, 3.4, 4.3, '项目驱动', 0, 118, 0.75, '支付、借贷、智能合约各讲一块，项目做一个链上借贷协议的原型并写商业计划书。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3206', 6.0, 3.5, 4.2, '案例驱动', 1, 189, 0.85, 'DCF、可比公司、可比交易三种方法，最后对一个真实并购案做完整估值。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3207', 8.0, 4.4, 3.7, '严格推导', 0, 84, 0.73, '布朗运动、伊藤引理、Black-Scholes 全推导，数学要求高，适合想读金融工程方向的人。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('FI3208', 4.0, 2.7, 4.5, '案例讲授', 1, 143, 0.8, '资产负债管理、信贷风险、巴塞尔协议，课程轻松，小组作业是做一家银行的年报分析。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('GE2201', 3.0, 2.1, 4.6, '讲授 + 读书', 0, 207, 0.84, '从亚当·斯密讲到凯恩斯，指定书目要真读，读书报告抄不得。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('GE2202', 2.0, 1.8, 4.7, '案例讨论', 1, 231, 0.86, '以商业丑闻案例为主，课堂发言计分，适合愿意开口的人刷分。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('GE2203', 3.0, 2.3, 4.5, '实验 + 讲授', 0, 266, 0.87, '讲启发式与偏误，和金融决策能互相印证，有两次简单行为实验。');
INSERT INTO course_profile (code, weekly_hours, difficulty, grading, style, attendance, sample_size, confidence, summary) VALUES ('GE2204', 3.0, 2.6, 4.3, '工作坊', 1, 102, 0.71, '小班工作坊，每两周交一稿并互评，对出国申请和英文论文写作帮助直接。');
INSERT INTO assessment (code, component, weight) VALUES ('FI3101', '期末', 50.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3101', '案例', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3101', '平时', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3102', '期末', 45.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3102', '作业', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3102', '组合报告', 25.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3103', '期末', 45.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3103', '编程作业', 35.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3103', '平时', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3104', '期末', 60.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3104', '作业', 25.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3104', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3201', '期末', 45.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3201', '项目', 35.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3201', '作业', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3202', '期末', 50.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3202', '建模作业', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3202', '平时', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3203', '期末', 55.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3203', '小组报告', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3203', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3204', '期末', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3204', '文献汇报', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3204', '平时', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3205', '项目', 55.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3205', '期末', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3205', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3206', '期末', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3206', '估值模型', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3206', '课堂', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3207', '期末', 60.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3207', '作业', 30.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3207', '平时', 10.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3208', '期末', 50.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3208', '小组作业', 35.0);
INSERT INTO assessment (code, component, weight) VALUES ('FI3208', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2201', '期末', 50.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2201', '读书报告', 35.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2201', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2202', '期末', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2202', '课堂讨论', 40.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2202', '出勤', 20.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2203', '期末', 45.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2203', '实验报告', 35.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2203', '平时', 15.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2204', '过程写作', 60.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2204', '期末', 25.0);
INSERT INTO assessment (code, component, weight) VALUES ('GE2204', '出勤', 15.0);
INSERT INTO teacher (name, rating) VALUES ('陆明轩', 4.8);
INSERT INTO teacher (name, rating) VALUES ('周雅琴', 4.2);
INSERT INTO teacher (name, rating) VALUES ('沈立诚', 4.6);
INSERT INTO teacher (name, rating) VALUES ('何静怡', 4.1);
INSERT INTO teacher (name, rating) VALUES ('顾承宇', 4.7);
INSERT INTO teacher (name, rating) VALUES ('许文倩', 3.9);
INSERT INTO teacher (name, rating) VALUES ('马国栋', 4.4);
INSERT INTO teacher (name, rating) VALUES ('林若菲', 4.0);
INSERT INTO teacher (name, rating) VALUES ('唐启帆', 4.8);
INSERT INTO teacher (name, rating) VALUES ('邓雨桐', 4.0);
INSERT INTO teacher (name, rating) VALUES ('秦子昂', 4.5);
INSERT INTO teacher (name, rating) VALUES ('谢婉清', 3.8);
INSERT INTO teacher (name, rating) VALUES ('程颂', 4.6);
INSERT INTO teacher (name, rating) VALUES ('苏沐', 4.0);
INSERT INTO teacher (name, rating) VALUES ('叶知秋', 4.9);
INSERT INTO teacher (name, rating) VALUES ('罗一鸣', 3.7);
INSERT INTO teacher (name, rating) VALUES ('韩卓', 4.5);
INSERT INTO teacher (name, rating) VALUES ('邱壑', 3.9);
INSERT INTO teacher (name, rating) VALUES ('闻人悦', 4.7);
INSERT INTO teacher (name, rating) VALUES ('胡绍', 4.1);
INSERT INTO teacher (name, rating) VALUES ('简牧', 4.6);
INSERT INTO teacher (name, rating) VALUES ('白泽', 3.8);
INSERT INTO teacher (name, rating) VALUES ('邵嘉禾', 4.4);
INSERT INTO teacher (name, rating) VALUES ('汤宁', 4.2);
INSERT INTO teacher (name, rating) VALUES ('严修远', 4.5);
INSERT INTO teacher (name, rating) VALUES ('李慕之', 4.1);
INSERT INTO teacher (name, rating) VALUES ('温言', 4.8);
INSERT INTO teacher (name, rating) VALUES ('许清和', 4.4);
INSERT INTO teacher (name, rating) VALUES ('沈砚', 4.9);
INSERT INTO teacher (name, rating) VALUES ('郑微', 4.6);
INSERT INTO teacher (name, rating) VALUES ('Emily Hart', 4.5);
INSERT INTO teacher (name, rating) VALUES ('陈默', 4.1);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3101-01', 'FI3101', '陆明轩', 0.28, 90, 90);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3101-02', 'FI3101', '周雅琴', 0.57, 90, 71);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3102-01', 'FI3102', '沈立诚', 0.31, 100, 98);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3102-02', 'FI3102', '何静怡', 0.62, 100, 66);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3103-01', 'FI3103', '顾承宇', 0.26, 80, 80);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3103-02', 'FI3103', '许文倩', 0.74, 80, 52);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3104-01', 'FI3104', '马国栋', 0.46, 110, 96);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3104-02', 'FI3104', '林若菲', 0.81, 110, 68);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3201-01', 'FI3201', '唐启帆', 0.19, 70, 70);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3201-02', 'FI3201', '邓雨桐', 0.55, 70, 47);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3202-01', 'FI3202', '秦子昂', 0.38, 80, 68);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3202-02', 'FI3202', '谢婉清', 0.79, 80, 52);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3203-01', 'FI3203', '程颂', 0.42, 90, 74);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3203-02', 'FI3203', '苏沐', 0.86, 90, 55);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3204-01', 'FI3204', '叶知秋', 0.33, 70, 69);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3204-02', 'FI3204', '罗一鸣', 0.88, 70, 41);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3205-01', 'FI3205', '韩卓', 0.49, 55, 43);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3205-02', 'FI3205', '邱壑', 0.77, 55, 38);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3206-01', 'FI3206', '闻人悦', 0.24, 80, 80);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3206-02', 'FI3206', '胡绍', 0.66, 80, 58);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3207-01', 'FI3207', '简牧', 0.35, 60, 52);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3207-02', 'FI3207', '白泽', 0.82, 60, 39);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3208-01', 'FI3208', '邵嘉禾', 0.64, 90, 62);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('FI3208-02', 'FI3208', '汤宁', 0.85, 90, 54);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2201-01', 'GE2201', '严修远', 0.61, 120, 92);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2201-02', 'GE2201', '李慕之', 0.8, 120, 78);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2202-01', 'GE2202', '温言', 0.4, 100, 95);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2202-02', 'GE2202', '许清和', 0.73, 100, 64);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2203-01', 'GE2203', '沈砚', 0.36, 100, 98);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2203-02', 'GE2203', '郑微', 0.84, 100, 58);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2204-01', 'GE2204', 'Emily Hart', 0.34, 30, 30);
INSERT INTO offering (id, code, teacher, admit_rate, capacity, enrolled) VALUES ('GE2204-02', 'GE2204', '陈默', 0.7, 30, 22);
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3101-01', 1, 1, 2, '安泰楼 A301');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3101-01', 3, 3, 4, '安泰楼 A301');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3101-02', 2, 3, 4, '安泰楼 B202');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3101-02', 4, 1, 2, '安泰楼 B202');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3102-01', 1, 3, 4, '安泰楼 A201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3102-01', 4, 6, 7, '安泰楼 A201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3102-02', 2, 1, 2, '安泰楼 B105');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3102-02', 5, 3, 4, '安泰楼 B105');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3103-01', 3, 1, 2, '安泰楼 C401');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3103-01', 5, 8, 9, '安泰楼 C401');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3103-02', 1, 6, 7, '安泰楼 C305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3103-02', 4, 3, 4, '安泰楼 C305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3104-01', 1, 8, 9, '安泰楼 A102');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3104-01', 3, 8, 9, '安泰楼 A102');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3104-02', 2, 10, 11, '安泰楼 B303');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3104-02', 5, 6, 7, '安泰楼 B303');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3201-01', 1, 6, 7, '安泰楼 C201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3201-01', 3, 6, 7, '安泰楼 C201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3201-02', 2, 3, 4, '安泰楼 C208');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3201-02', 4, 10, 11, '安泰楼 C208');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3202-01', 2, 8, 9, '安泰楼 B401');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3202-01', 4, 3, 4, '安泰楼 B401');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3202-02', 3, 10, 11, '安泰楼 B405');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3202-02', 5, 1, 2, '安泰楼 B405');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3203-01', 5, 1, 2, '安泰楼 A405');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3203-01', 3, 10, 11, '安泰楼 A405');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3203-02', 1, 3, 4, '安泰楼 A407');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3203-02', 4, 8, 9, '安泰楼 A407');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3204-01', 4, 1, 2, '安泰楼 B201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3204-01', 2, 6, 7, '安泰楼 B201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3204-02', 5, 3, 4, '安泰楼 B205');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3204-02', 1, 1, 2, '安泰楼 B205');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3205-01', 2, 10, 11, '安泰楼 C102');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3205-01', 4, 1, 2, '安泰楼 C102');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3205-02', 3, 1, 2, '安泰楼 C105');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3205-02', 5, 10, 11, '安泰楼 C105');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3206-01', 1, 10, 11, '安泰楼 A305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3206-01', 3, 1, 2, '安泰楼 A305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3206-02', 4, 6, 7, '安泰楼 A308');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3206-02', 2, 1, 2, '安泰楼 A308');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3207-01', 3, 3, 4, '安泰楼 C301');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3207-01', 5, 10, 11, '安泰楼 C301');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3207-02', 1, 6, 7, '安泰楼 C305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3207-02', 4, 10, 11, '安泰楼 C305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3208-01', 2, 1, 2, '安泰楼 B501');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3208-01', 5, 6, 7, '安泰楼 B501');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3208-02', 4, 8, 9, '安泰楼 B503');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('FI3208-02', 1, 3, 4, '安泰楼 B503');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2201-01', 3, 8, 9, '人文楼 2-301');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2201-02', 5, 6, 7, '人文楼 2-305');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2202-01', 2, 3, 4, '人文楼 1-201');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2202-02', 4, 8, 9, '人文楼 1-205');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2203-01', 5, 3, 4, '人文楼 3-108');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2203-02', 1, 10, 11, '人文楼 3-112');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2204-01', 4, 10, 11, '外语楼 3-205');
INSERT INTO session (offering_id, day, start, "end", location) VALUES ('GE2204-02', 3, 10, 11, '外语楼 3-207');
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3101', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3102', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3103', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3104', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3201', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3202', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3203', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3204', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3205', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3206', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3207', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'FI3208', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'GE2201', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'GE2202', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'GE2203', 5);
INSERT INTO plan_item (term, major, grade, code, suggest_term) VALUES ('2026-2027-1', '金融学', 2024, 'GE2204', 5);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 4, '2026-11-23T15:32:06.150710+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 1, '2026-11-25T03:00:11.082109+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 1, '2026-11-23T15:12:01.793765+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 1, '2026-11-23T15:18:38.126771+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 1, '2026-11-25T03:00:33.796306+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 3, '2026-11-23T15:11:58.082102+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 2, '2026-11-23T15:23:39.442725+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 1, '2026-11-23T15:12:00.273774+00:00', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO student (id, revision, created_at, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('01169fb8-9403-4c28-84c0-ba3c562d249e', 0, NULL, '同学', NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL);
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'PE1001');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'MATH1101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'MATH1201');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'MATH2201');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'ECON1101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'ECON2101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'ECON2102');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'ACC2101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'STAT2101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'MGT1101');
INSERT INTO student_completed (student_id, code) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'PE1001');
INSERT INTO student_interest (student_id, tag) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('1da965fe-dd34-43b6-9759-fe0ec115f51d', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('69fcd4b1-4596-409b-b8da-4273f616a63b', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('98151c38-0c52-497c-afc6-1943aa99ee31', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('ababfcf3-530a-4303-bfac-10186f1755b7', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '实证');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '计量');
INSERT INTO student_interest (student_id, tag) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '量化');
INSERT INTO student_interest (student_id, tag) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '工程');
INSERT INTO student_interest (student_id, tag) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', '系统');
INSERT INTO student_interest (student_id, tag) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', 'AI');
INSERT INTO student_interest (student_id, tag) VALUES ('e8a6aead-1cc2-4811-9fea-c750b59a5d9c', '工程');
INSERT INTO student_blocked (student_id, value) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '{"day": 3, "start": 5, "end": 9, "weeks": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], "location": "个人安排"}');
INSERT INTO draft (student_id, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO draft (student_id, name, major, grade, goal, focus, challenge, exploration, avoid_early, min_credits, max_credits) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '同学', '金融学', 2024, '保研', 0.5, 0.5, 0.5, 1, 18.0, 24.0);
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'MATH1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'MATH1201');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'MATH2201');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'ECON1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'ECON2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'ECON2102');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'ACC2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'STAT2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'MGT1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'completed', 'PE1001');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', '系统');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', 'AI');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', '工程');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', '实证');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', '计量');
INSERT INTO draft_item (student_id, kind, value) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', 'interests', '量化');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'MATH1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'MATH1201');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'MATH2201');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'ECON1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'ECON2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'ECON2102');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'ACC2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'STAT2101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'MGT1101');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'completed', 'PE1001');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', '系统');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', 'AI');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', '工程');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', '实证');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', '计量');
INSERT INTO draft_item (student_id, kind, value) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', 'interests', '量化');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '2026-11-23T15:32:06.365697+00:00', 0, '我', '我想学数据分析');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '2026-11-23T15:32:06.365697+00:00', 1, '选课咨询', '好的，我会关注实证、计量、量化。可以按这些安排更新课表。');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.450043+00:00', 0, '我', '我想学数据分析，周三下午要实习');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.450043+00:00', 1, '选课咨询', '好的，我会关注实证、计量、量化、避开周三下午。可以按这些安排更新课表。');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.568607+00:00', 0, '选课咨询', '课表已更新，你可以在课表区域比较方案。');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '2026-11-23T15:23:39.641642+00:00', 0, '我', '我想学数据分析');
INSERT INTO message (student_id, time, seq, role, text) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '2026-11-23T15:23:39.641642+00:00', 1, '选课咨询', '好的，我会关注实证、计量、量化。可以按这些安排更新课表。');
INSERT INTO evidence (student_id, time, source, provider) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '2026-11-23T15:32:06.365697+00:00', '我想学数据分析', 'local-rules');
INSERT INTO evidence (student_id, time, source, provider) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.450043+00:00', '我想学数据分析，周三下午要实习', 'local-rules');
INSERT INTO evidence (student_id, time, source, provider) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '2026-11-23T15:23:39.641642+00:00', '我想学数据分析', 'local-rules');
INSERT INTO evidence_change (student_id, time, seq, change) VALUES ('15945ed4-33b9-4b6a-912a-26fd99a822a4', '2026-11-23T15:32:06.365697+00:00', 0, '关注实证、计量、量化');
INSERT INTO evidence_change (student_id, time, seq, change) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.450043+00:00', 0, '关注实证、计量、量化');
INSERT INTO evidence_change (student_id, time, seq, change) VALUES ('b2af636c-d841-4e60-81f7-2ed608237b9b', '2026-11-23T15:11:58.450043+00:00', 1, '避开周三下午');
INSERT INTO evidence_change (student_id, time, seq, change) VALUES ('e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4', '2026-11-23T15:23:39.641642+00:00', 0, '关注实证、计量、量化');
INSERT INTO users (username, salt, digest, student_id) VALUES ('check_e0a0148d0d', 'eeb4327bea0f74010d26e4d69c4fa782', 'c19984130cb2e49b270782b12573e4a139ff9f745e6414a64625c9186ab6d4fe94b710d9aff79053a34b683b54a831f01c2212715a7a040e4d475d802cb07a0d', 'e6faa30a-cf3f-4d10-a691-87c3d6f7ccc4');
INSERT INTO users (username, salt, digest, student_id) VALUES ('check_90b9829045', '019b8136bb16357cfc3a6f139aa53c10', 'aafba06cb6861aec7518df6a3f385378f5a78eea62c2b4693125b855bdfd0c1b79038e308dd37cad8a6b644efa08bb25d1044ed15f62419e95a0f7497e9a6378', '15945ed4-33b9-4b6a-912a-26fd99a822a4');
INSERT INTO users (username, salt, digest, student_id) VALUES ('kaisch314', '3789c5e66763fc62fd8c388fee5f335f', 'a490608d90e30bbcef137bbcae9b48e1a05e50dd384245e66327d7270d45a006be081e20f8e22045e110c698529d1165fc5fca7327a1ed2cc7124cf2b634d4b4', '1da965fe-dd34-43b6-9759-fe0ec115f51d');
INSERT INTO users (username, salt, digest, student_id) VALUES ('123', '46a0b2cd9c6cf84553c8db1b927f19bc', 'dbea30cd7c44d54e6b2f35137474da485f6dd4fe90115a687b42357f7a8a1b40f6e3309935f5c7a4f716b52db33107eced283bed63a2d356993945386c500416', 'ababfcf3-530a-4303-bfac-10186f1755b7');
INSERT INTO users (username, salt, digest, student_id) VALUES ('demo', '56659049bbd31bfe4827335cbbbbc955', '9378519f23b0d255ac35b120776df0983c7c155d0162a7688beace7077812974d6b5ad86307faec919726f5f48418efdc2817d44b5e2ad3a4ba5d9def573aa94', '01169fb8-9403-4c28-84c0-ba3c562d249e');
INSERT INTO sessions (token_hash, username, expires) VALUES ('ae8fe73f6c84ec853910c1abe5d8b34b3b4cd9717889aa57dbebd695bffb94a7', 'kaisch314', 1795662010.7464871);
INSERT INTO sessions (token_hash, username, expires) VALUES ('0116c93765833fc8d0486e7f27a3a211a9bd1d161248448ee3a015c1f618c10c', 'demo', 1795662299.386492);
INSERT INTO sessions (token_hash, username, expires) VALUES ('002d91faf679813e9ed84a8f8431f5edeb966bacfa86771b4d34044a59935e2e', '123', 1795670557.108387);
COMMIT;