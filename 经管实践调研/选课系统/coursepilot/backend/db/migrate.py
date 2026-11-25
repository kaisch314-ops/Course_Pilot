# -*- coding: utf-8 -*-
"""把 seed.json + auth.sqlite3 + students/*.json 迁移到 BCNF 关系库 coursepilot.db。"""
import json
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "data"
DB = DATA / "coursepilot.db"

def main():
    seed = json.loads((DATA / "seed.json").read_text(encoding="utf-8"))
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((BACKEND / "db" / "schema.sql").read_text(encoding="utf-8"))
    cur = con.cursor()

    # ---- 参考数据域 ----
    cur.execute("INSERT INTO major VALUES (?, ?)", (seed["major"], seed["college"]))
    term_key = (seed["term"], seed["major"], seed["grade"])
    cur.execute("INSERT INTO term_config VALUES (?, ?, ?, ?)", (*term_key, seed.get("notice", "")))
    for r in seed["requirements"]:
        cur.execute("INSERT INTO module_req VALUES (?, ?, ?, ?, ?)", (*term_key, r["module"], r["min_credits"]))
    for module, credits in seed.get("graduation", {}).items():
        cur.execute("INSERT INTO graduation_req VALUES (?, ?, ?, ?, ?)", (*term_key, module, credits))
    for module, credits in seed.get("earned", {}).items():
        cur.execute("INSERT INTO earned_default VALUES (?, ?, ?, ?, ?)", (*term_key, module, credits))
    for code in seed.get("completed", []):
        cur.execute("INSERT INTO default_completed VALUES (?, ?, ?, ?)", (*term_key, code))

    for c in seed["courses"]:
        cur.execute("INSERT INTO course VALUES (?, ?, ?, ?)",
                    (c["code"], c["name"], c["credits"], c["category"]))
        for tag in c.get("tags", []):
            cur.execute("INSERT INTO course_tag VALUES (?, ?)", (c["code"], tag))
        for pre in c.get("prereqs", []):
            cur.execute("INSERT INTO prereq VALUES (?, ?)", (c["code"], pre))
        p = c.get("profile")
        if p:
            cur.execute("INSERT INTO course_profile VALUES (?,?,?,?,?,?,?,?,?)",
                        (c["code"], p.get("weekly_hours"), p.get("difficulty"), p.get("grading"),
                         p.get("style"), int(bool(p.get("attendance"))), p.get("sample_size"),
                         p.get("confidence"), p.get("summary")))
            for comp, w in p.get("assessment", {}).items():
                cur.execute("INSERT INTO assessment VALUES (?, ?, ?)", (c["code"], comp, w))

    teachers = {}
    for o in seed["offerings"]:
        if o["teacher"] in teachers and teachers[o["teacher"]] != o["teacher_rating"]:
            print(f"警告：教师 {o['teacher']} 评分不一致，违反 teacher → rating，无法拆表", file=sys.stderr)
            sys.exit(1)
        teachers[o["teacher"]] = o["teacher_rating"]
    for name, rating in teachers.items():
        cur.execute("INSERT INTO teacher VALUES (?, ?)", (name, rating))
    for o in seed["offerings"]:
        cur.execute("INSERT INTO offering VALUES (?, ?, ?, ?, ?, ?)",
                    (o["id"], o["code"], o["teacher"], o.get("admit_rate"), o.get("capacity"), o.get("enrolled")))
        for s in o.get("sessions", []):
            cur.execute("INSERT INTO session VALUES (?, ?, ?, ?, ?)",
                        (o["id"], s["day"], s["start"], s["end"], s.get("location", "")))

    for p in seed["plan"]:
        cur.execute("INSERT INTO plan_item VALUES (?, ?, ?, ?, ?)",
                    (*term_key, p["code"], p.get("suggest_term")))

    # ---- 学生档案域 ----
    PROFILE_COLS = ("name", "major", "grade", "goal", "focus", "challenge",
                    "exploration", "avoid_early", "min_credits", "max_credits")
    for path in sorted((DATA / "students").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        sid = doc["id"]
        p = doc["profile"]
        cur.execute(
            "INSERT INTO student VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, doc.get("revision", 0), doc.get("created_at"),
             p.get("name"), p.get("major"), p.get("grade"), p.get("goal"),
             p.get("focus"), p.get("challenge"), p.get("exploration"),
             int(bool(p.get("avoid_early"))), p.get("min_credits"), p.get("max_credits")))
        for code in p.get("completed", []):
            cur.execute("INSERT INTO student_completed VALUES (?, ?)", (sid, code))
        for tag in p.get("interests", []):
            cur.execute("INSERT INTO student_interest VALUES (?, ?)", (sid, tag))
        for table, key in (("student_locked", "locked"), ("student_excluded", "excluded"),
                           ("student_blocked", "blocked")):
            for v in p.get(key, []):
                cur.execute(f"INSERT INTO {table} VALUES (?, ?)", (sid, json.dumps(v, ensure_ascii=False)))
        for course, w in (p.get("affinity") or {}).items():
            cur.execute("INSERT INTO student_affinity VALUES (?, ?, ?)", (sid, course, w))

        d = doc.get("draft")
        if d:
            cur.execute("INSERT INTO draft VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, d.get("name"), d.get("major"), d.get("grade"), d.get("goal"),
                         d.get("focus"), d.get("challenge"), d.get("exploration"),
                         int(bool(d.get("avoid_early"))), d.get("min_credits"), d.get("max_credits")))
            for kind in ("completed", "interests", "locked", "excluded", "blocked"):
                for v in d.get(kind, []):
                    cur.execute("INSERT INTO draft_item VALUES (?, ?, ?)",
                                (sid, kind, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)))

        msg_seq = {}
        for m in doc.get("messages", []):
            seq = msg_seq.get(m["time"], 0)
            msg_seq[m["time"]] = seq + 1
            cur.execute("INSERT INTO message VALUES (?, ?, ?, ?, ?)",
                        (sid, m["time"], seq, m["role"], m["text"]))
        for f in doc.get("feedback", []):
            cur.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (f["id"], sid, f["course"], f.get("reason"), f.get("direction"),
                         f["time"], f.get("source")))
        for e in doc.get("evidence", []):
            cur.execute("INSERT INTO evidence VALUES (?, ?, ?, ?)",
                        (sid, e["time"], e.get("source"), e.get("provider")))
            for i, ch in enumerate(e.get("changes", [])):
                cur.execute("INSERT INTO evidence_change VALUES (?, ?, ?, ?)",
                            (sid, e["time"], i, str(ch)))
        for o in doc.get("outcome_history", []):
            cur.execute("INSERT INTO outcome_history VALUES (?, ?, ?)",
                        (sid, o["time"], json.dumps(o, ensure_ascii=False)))

    # ---- 认证域（原 auth.sqlite3）----
    # 注册账号时不会立刻生成档案，先补占位学生行以保住外键
    auth = sqlite3.connect(DATA / "auth.sqlite3")
    user_rows = list(auth.execute("SELECT username, salt, digest, student_id FROM users"))
    for _, _, _, sid in user_rows:
        cur.execute(
            "INSERT OR IGNORE INTO student (id, revision, name, avoid_early) VALUES (?, 0, '同学', 1)",
            (sid,))
    for row in user_rows:
        cur.execute("INSERT INTO users VALUES (?, ?, ?, ?)", row)
    for row in auth.execute("SELECT token_hash, username, expires FROM sessions"):
        cur.execute("INSERT INTO sessions VALUES (?, ?, ?)", row)
    auth.close()

    con.commit()
    bad = list(con.execute("PRAGMA foreign_key_check"))
    if bad:
        print("外键校验失败:", bad, file=sys.stderr)
        sys.exit(1)
    print("迁移完成 ->", DB)
    for t in ["major", "term_config", "module_req", "graduation_req", "earned_default",
              "default_completed", "course", "course_tag", "prereq", "course_profile",
              "assessment", "teacher", "offering", "session", "plan_item",
              "student", "student_completed", "student_interest", "draft", "draft_item",
              "message", "feedback", "evidence", "evidence_change", "users", "sessions"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:20s} {n}")
    con.close()

if __name__ == "__main__":
    main()
