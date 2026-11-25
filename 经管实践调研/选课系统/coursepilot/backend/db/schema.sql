-- CoursePilot BCNF 关系模式（SQLite 方言）
-- 设计原则：
--   1. 所有多值属性拆为独立从表（达到 1NF/4NF）
--   2. 消除传递依赖：TEACHER 独立（teacher → teacher_rating）；
--      PLAN_ITEM 删除 module（由 COURSE.category 决定）；MAJOR 独立（major → college）
--   3. 每个非平凡函数依赖的决定因素均为超码 → BCNF
--   4. FEEDBACK 不存 tags（由 course 决定，快照冗余，消除传递依赖）

PRAGMA foreign_keys = ON;

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
    end         INTEGER NOT NULL,
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

-- ========== 教师端（运行时由 app/teacher.py 创建，coursepilot.db） ==========

-- 注：教师端上线后 users 表扩展了 role（student/teacher，默认 student）与
-- teacher_name（仅教师）两列；旧表由 app/auth.py 在线迁移（重建拷贝）。

-- 教师课程简介，(teacher, course_code) 为码
CREATE TABLE IF NOT EXISTS teacher_intro (
    teacher     TEXT NOT NULL,
    course_code TEXT NOT NULL,
    style       TEXT NOT NULL DEFAULT '',   -- 教学方式
    attendance  TEXT NOT NULL DEFAULT '',   -- 点名方式
    assessment  TEXT NOT NULL DEFAULT '',   -- 考核方式
    expectation TEXT NOT NULL DEFAULT '',   -- 期望的学生
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (teacher, course_code)
);

-- 师生问答（Q&A 论坛）：学生提问、教师回复，全员可见
CREATE TABLE IF NOT EXISTS qa_question (
    id           TEXT PRIMARY KEY,
    course_code  TEXT NOT NULL,
    teacher      TEXT NOT NULL,
    student_id   TEXT NOT NULL,
    student_name TEXT NOT NULL,
    text         TEXT NOT NULL,
    time         TEXT NOT NULL,
    answer       TEXT,
    answer_time  TEXT
);

-- AI 总结缓存：kind ∈ {reviews 社区评价, preferences 学生偏好, advice 改进建议}
-- source ∈ {rules 本地规则, llm 大模型}
CREATE TABLE IF NOT EXISTS ai_summary_cache (
    teacher      TEXT NOT NULL,
    course_code  TEXT NOT NULL,
    kind         TEXT NOT NULL,
    content      TEXT NOT NULL,
    source       TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    PRIMARY KEY (teacher, course_code, kind)
);
