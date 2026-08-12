from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from .assignments import ASSIGNMENTS
from .bug_lab import DEFAULT_BUG_PROBLEMS
from .config import DATA_DIR
from .human_code import DEFAULT_HUMAN_CODE_PROBLEMS


DB_PATH = Path(os.getenv("AIP1_DB_PATH", DATA_DIR / "aip1_studio.sqlite3"))
SESSION_SECONDS = 60 * 60 * 24 * 14
PBKDF2_ITERATIONS = 200_000


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin')),
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assignment_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('unlocked', 'completed')),
                best_code TEXT NOT NULL DEFAULT '',
                completed_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, assignment_id)
            );

            CREATE TABLE IF NOT EXISTS manual_unlocks (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assignment_id TEXT NOT NULL,
                unlocked_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                unlocked_at TEXT NOT NULL,
                PRIMARY KEY (user_id, assignment_id)
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assignment_id TEXT NOT NULL,
                code TEXT NOT NULL,
                passed INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assignment_drafts (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assignment_id TEXT NOT NULL,
                code TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, assignment_id)
            );

            CREATE TABLE IF NOT EXISTS behavior_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assignment_id TEXT,
                event_type TEXT NOT NULL,
                code_len INTEGER NOT NULL DEFAULT 0,
                inserted_len INTEGER NOT NULL DEFAULT 0,
                deleted_len INTEGER NOT NULL DEFAULT 0,
                dt_ms INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                slug TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                creator TEXT NOT NULL,
                description TEXT NOT NULL,
                template_id TEXT NOT NULL,
                code TEXT NOT NULL,
                tests TEXT NOT NULL,
                specification TEXT NOT NULL,
                ai_record TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bug_problems (
                id TEXT PRIMARY KEY,
                activity_type TEXT NOT NULL DEFAULT 'bug',
                title TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                description TEXT NOT NULL,
                function_name TEXT NOT NULL,
                reasoning_trace TEXT NOT NULL,
                llm_code TEXT NOT NULL,
                ground_truth_code TEXT NOT NULL,
                initial_tests TEXT NOT NULL DEFAULT '[]',
                hidden_tests TEXT NOT NULL DEFAULT '[]',
                min_student_tests INTEGER NOT NULL DEFAULT 10,
                position INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bug_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                problem_id TEXT NOT NULL REFERENCES bug_problems(id) ON DELETE CASCADE,
                stage TEXT NOT NULL CHECK(stage IN ('tests', 'fix')),
                student_tests TEXT NOT NULL,
                corrected_code TEXT NOT NULL DEFAULT '',
                passed INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bug_generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                problem_id TEXT NOT NULL REFERENCES bug_problems(id) ON DELETE CASCADE,
                reasoning_trace TEXT NOT NULL,
                llm_code TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS human_code_drafts (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                problem_id TEXT NOT NULL REFERENCES bug_problems(id) ON DELETE CASCADE,
                solution_code TEXT NOT NULL DEFAULT '',
                test_code TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, problem_id)
            );

            CREATE TABLE IF NOT EXISTS human_code_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                problem_id TEXT NOT NULL REFERENCES bug_problems(id) ON DELETE CASCADE,
                solution_code TEXT NOT NULL,
                passed INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_user_assignment
                ON behavior_events(user_id, assignment_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_user_assignment
                ON submissions(user_id, assignment_id);
            CREATE INDEX IF NOT EXISTS idx_assignment_drafts_user_assignment
                ON assignment_drafts(user_id, assignment_id);
            CREATE INDEX IF NOT EXISTS idx_bug_submissions_user_problem
                ON bug_submissions(user_id, problem_id);
            CREATE INDEX IF NOT EXISTS idx_bug_generations_user_problem
                ON bug_generations(user_id, problem_id);
            CREATE INDEX IF NOT EXISTS idx_human_submissions_user_problem
                ON human_code_submissions(user_id, problem_id);
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bug_problems)").fetchall()}
        if "hidden_tests" not in columns:
            conn.execute("ALTER TABLE bug_problems ADD COLUMN hidden_tests TEXT NOT NULL DEFAULT '[]'")
            if "initial_tests" in columns:
                conn.execute("UPDATE bug_problems SET hidden_tests = initial_tests")
            for problem in DEFAULT_BUG_PROBLEMS:
                conn.execute(
                    "UPDATE bug_problems SET hidden_tests = ? WHERE id = ?",
                    (json.dumps(problem["hidden_tests"]), problem["id"]),
                )
        if "activity_type" not in columns:
            conn.execute("ALTER TABLE bug_problems ADD COLUMN activity_type TEXT NOT NULL DEFAULT 'bug'")
        conn.execute("UPDATE bug_problems SET activity_type = 'bug' WHERE activity_type = 'both'")
    seed_bug_problems()
    seed_admin()


def seed_bug_problems() -> None:
    now = iso_now()
    with connect() as conn:
        for activity_type, problem_set in (("bug", DEFAULT_BUG_PROBLEMS), ("human", DEFAULT_HUMAN_CODE_PROBLEMS)):
            for problem in problem_set:
                conn.execute(
                """
                INSERT INTO bug_problems
                    (id, activity_type, title, difficulty, description, function_name, reasoning_trace, llm_code,
                     ground_truth_code, initial_tests, hidden_tests, min_student_tests, position, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    activity_type = excluded.activity_type,
                    reasoning_trace = excluded.reasoning_trace
                """,
                (
                    problem["id"], activity_type, problem["title"], problem["difficulty"], problem["description"],
                    problem["function_name"], problem["reasoning_trace"], problem["llm_code"],
                    problem["ground_truth_code"], "[]", json.dumps(problem["hidden_tests"]),
                    problem["min_student_tests"], problem["position"], int(problem["active"]), now, now,
                ),
            )


def seed_admin() -> None:
    username = os.getenv("AIP1_ADMIN_USERNAME", "admin")
    password = os.getenv("AIP1_ADMIN_PASSWORD", "admin123")
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            create_user(
                username=username,
                password=password,
                display_name="Course Admin",
                role="admin",
                must_change_password=True,
                conn=conn,
            )


def create_user(
    *,
    username: str,
    password: str,
    display_name: str,
    role: str = "student",
    must_change_password: bool = True,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    username = username.strip().lower()
    display_name = display_name.strip() or username
    if not username:
        raise ValueError("username is required")
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    if role not in ("student", "admin"):
        raise ValueError("invalid role")

    own_conn = conn is None
    conn = conn or connect()
    try:
        now = iso_now()
        cur = conn.execute(
            """
            INSERT INTO users (username, display_name, role, password_hash, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, display_name, role, hash_password(password), int(must_change_password), now),
        )
        user_id = int(cur.lastrowid)
        first_assignment = ASSIGNMENTS[0]["id"]
        conn.execute(
            """
            INSERT INTO progress (user_id, assignment_id, status, updated_at)
            VALUES (?, ?, 'unlocked', ?)
            """,
            (user_id, first_assignment, now),
        )
        if own_conn:
            conn.commit()
        return get_user_by_id(user_id, conn=conn) or {}
    finally:
        if own_conn:
            conn.close()


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    with connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            return None
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (iso_now(), user["id"]))
        return dict(user)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_SECONDS
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, expires_at, iso_now()),
        )
    return token


def delete_session(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_for_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, int(time.time())),
        ).fetchone()
        if not row:
            return None
        return dict(row)


def get_user_by_id(user_id: int, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    own_conn = conn is None
    conn = conn or connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> None:
    if len(new_password) < 6:
        raise ValueError("new password must be at least 6 characters")
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(old_password, row["password_hash"]):
            raise ValueError("current password is incorrect")
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
            (hash_password(new_password), user_id),
        )


def reset_password(user_id: int, new_password: str) -> None:
    if len(new_password) < 6:
        raise ValueError("new password must be at least 6 characters")
    with connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
            (hash_password(new_password), user_id),
        )


def completed_assignment_ids(user_id: int) -> set[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT assignment_id FROM progress WHERE user_id = ? AND status = 'completed'",
            (user_id,),
        ).fetchall()
        return {row["assignment_id"] for row in rows}


def manual_unlock_ids(user_id: int) -> set[str]:
    with connect() as conn:
        rows = conn.execute("SELECT assignment_id FROM manual_unlocks WHERE user_id = ?", (user_id,)).fetchall()
        return {row["assignment_id"] for row in rows}


def is_assignment_unlocked(user: dict[str, Any], assignment_id: str) -> bool:
    if user["role"] == "admin":
        return True
    ids = [assignment["id"] for assignment in ASSIGNMENTS]
    if assignment_id not in ids:
        return False
    completed = completed_assignment_ids(user["id"])
    manual = manual_unlock_ids(user["id"])
    if assignment_id in manual:
        return True
    index = ids.index(assignment_id)
    if index == 0:
        return True
    previous_ids = ids[:index]
    return all(item in completed for item in previous_ids)


def assignment_drafts(user_id: int) -> dict[str, dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT assignment_id, code, updated_at FROM assignment_drafts WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {row["assignment_id"]: {"code": row["code"], "updated_at": row["updated_at"]} for row in rows}


def assignment_draft(user_id: int, assignment_id: str) -> dict[str, str] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT code, updated_at FROM assignment_drafts WHERE user_id = ? AND assignment_id = ?",
            (user_id, assignment_id),
        ).fetchone()
        return {"code": row["code"], "updated_at": row["updated_at"]} if row else None


def save_assignment_draft(user_id: int, assignment_id: str, code: str) -> dict[str, str]:
    now = iso_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO assignment_drafts (user_id, assignment_id, code, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, assignment_id)
            DO UPDATE SET code = excluded.code, updated_at = excluded.updated_at
            """,
            (user_id, assignment_id, code, now),
        )
    return {"assignment_id": assignment_id, "code": code, "updated_at": now}


def record_submission(user_id: int, assignment_id: str, code: str, result: dict[str, Any]) -> None:
    save_assignment_draft(user_id, assignment_id, code)
    now = iso_now()
    passed = bool(result.get("passed"))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO submissions (user_id, assignment_id, code, passed, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, assignment_id, code, int(passed), json.dumps(result), now),
        )
        if passed:
            conn.execute(
                """
                INSERT INTO progress (user_id, assignment_id, status, best_code, completed_at, updated_at)
                VALUES (?, ?, 'completed', ?, ?, ?)
                ON CONFLICT(user_id, assignment_id)
                DO UPDATE SET status = 'completed', best_code = excluded.best_code,
                    completed_at = COALESCE(progress.completed_at, excluded.completed_at),
                    updated_at = excluded.updated_at
                """,
                (user_id, assignment_id, code, now, now),
            )
            _unlock_next(conn, user_id, assignment_id, now)


def _unlock_next(conn: sqlite3.Connection, user_id: int, assignment_id: str, now: str) -> None:
    ids = [assignment["id"] for assignment in ASSIGNMENTS]
    if assignment_id not in ids:
        return
    index = ids.index(assignment_id)
    if index + 1 >= len(ids):
        return
    conn.execute(
        """
        INSERT INTO progress (user_id, assignment_id, status, updated_at)
        VALUES (?, ?, 'unlocked', ?)
        ON CONFLICT(user_id, assignment_id) DO NOTHING
        """,
        (user_id, ids[index + 1], now),
    )


def log_events(user_id: int, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    now = iso_now()
    rows = []
    for event in events[:200]:
        rows.append(
            (
                user_id,
                str(event.get("assignment_id") or "")[:120],
                str(event.get("event_type") or "unknown")[:80],
                int(event.get("code_len") or 0),
                int(event.get("inserted_len") or 0),
                int(event.get("deleted_len") or 0),
                int(event.get("dt_ms") or 0),
                json.dumps(event.get("metadata") or {}),
                now,
            )
        )
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO behavior_events
                (user_id, assignment_id, event_type, code_len, inserted_len, deleted_len, dt_ms, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def admin_overview() -> dict[str, Any]:
    with connect() as conn:
        users = [dict(row) for row in conn.execute("SELECT id, username, display_name, role, created_at, last_login_at FROM users ORDER BY id")]
        progress_rows = conn.execute(
            """
            SELECT user_id,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_count
            FROM progress
            GROUP BY user_id
            """
        ).fetchall()
        progress_by_user = {row["user_id"]: row["completed_count"] for row in progress_rows}
        behavior_rows = conn.execute(
            """
            SELECT user_id,
                   COUNT(*) AS event_count,
                   SUM(CASE WHEN event_type = 'paste_attempt' THEN 1 ELSE 0 END) AS paste_attempts,
                   SUM(CASE WHEN inserted_len >= 20 THEN 1 ELSE 0 END) AS large_insertions,
                   SUM(CASE WHEN event_type = 'run' THEN 1 ELSE 0 END) AS run_count,
                   SUM(CASE WHEN event_type = 'submit' THEN 1 ELSE 0 END) AS submit_count
            FROM behavior_events
            GROUP BY user_id
            """
        ).fetchall()
        behavior_by_user = {row["user_id"]: dict(row) for row in behavior_rows}
        for user in users:
            behavior = behavior_by_user.get(user["id"], {})
            paste_attempts = int(behavior.get("paste_attempts") or 0)
            large_insertions = int(behavior.get("large_insertions") or 0)
            run_count = int(behavior.get("run_count") or 0)
            submit_count = int(behavior.get("submit_count") or 0)
            user["completed_count"] = int(progress_by_user.get(user["id"]) or 0)
            user["event_count"] = int(behavior.get("event_count") or 0)
            user["paste_attempts"] = paste_attempts
            user["large_insertions"] = large_insertions
            user["run_count"] = run_count
            user["submit_count"] = submit_count
            user["risk_score"] = paste_attempts * 10 + large_insertions * 4 + max(0, submit_count - run_count) * 2
        submissions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT submissions.id, users.username, submissions.assignment_id, submissions.passed, submissions.created_at
                FROM submissions
                JOIN users ON users.id = submissions.user_id
                ORDER BY submissions.id DESC
                LIMIT 50
                """
            )
        ]
        return {"users": users, "submissions": submissions, "assignment_count": len(ASSIGNMENTS)}


def unlock_assignment(user_id: int, assignment_id: str, admin_id: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO manual_unlocks (user_id, assignment_id, unlocked_by, unlocked_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, assignment_id) DO UPDATE SET unlocked_at = excluded.unlocked_at
            """,
            (user_id, assignment_id, admin_id, iso_now()),
        )


def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT slug, title, creator, description, template_id, created_at, updated_at FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_project(slug: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
        return dict(row) if row else None


def list_bug_problems(
    user_id: int | None = None,
    include_inactive: bool = False,
    activity_type: str | None = "bug",
) -> list[dict[str, Any]]:
    clauses = []
    parameters: list[Any] = []
    if not include_inactive:
        clauses.append("active = 1")
    if activity_type:
        clauses.append("activity_type = ?")
        parameters.append(activity_type)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM bug_problems {where} ORDER BY position, id", parameters).fetchall()
        progress: dict[str, dict[str, Any]] = {}
        if user_id is not None:
            progress_rows = conn.execute(
                """
                SELECT problem_id,
                       MAX(CASE WHEN stage = 'tests' AND passed = 1 THEN 1 ELSE 0 END) AS tests_passed,
                       MAX(CASE WHEN stage = 'fix' AND passed = 1 THEN 1 ELSE 0 END) AS completed
                FROM bug_submissions WHERE user_id = ? GROUP BY problem_id
                """,
                (user_id,),
            ).fetchall()
            progress = {
                row["problem_id"]: {"tests_passed": bool(row["tests_passed"]), "completed": bool(row["completed"])}
                for row in progress_rows
            }
            saved_test_rows = conn.execute(
                """
                SELECT submission.problem_id, submission.student_tests
                FROM bug_submissions AS submission
                WHERE submission.user_id = ? AND submission.stage = 'tests' AND submission.passed = 1
                  AND submission.id = (
                      SELECT MAX(latest.id) FROM bug_submissions AS latest
                      WHERE latest.user_id = submission.user_id
                        AND latest.problem_id = submission.problem_id
                        AND latest.stage = 'tests' AND latest.passed = 1
                  )
                """,
                (user_id,),
            ).fetchall()
            for row in saved_test_rows:
                saved_source = row["student_tests"]
                # Pre-migration submissions stored JSON cases. They cannot be restored as Python tests.
                if not saved_source.lstrip().startswith("["):
                    progress.setdefault(row["problem_id"], {"tests_passed": True, "completed": False})["student_test_code"] = saved_source
            for item in progress.values():
                if item.get("tests_passed") and "student_test_code" not in item:
                    item["tests_passed"] = False
        generations: dict[str, dict[str, Any]] = {}
        if user_id is not None:
            generation_rows = conn.execute(
                """
                SELECT generation.* FROM bug_generations AS generation
                WHERE generation.user_id = ? AND generation.id = (
                    SELECT MAX(latest.id) FROM bug_generations AS latest
                    WHERE latest.user_id = generation.user_id
                      AND latest.problem_id = generation.problem_id
                )
                """,
                (user_id,),
            ).fetchall()
            generations = {row["problem_id"]: dict(row) for row in generation_rows}
        return [public_bug_problem(dict(row), progress.get(row["id"], {}), generations.get(row["id"])) for row in rows]


def get_bug_problem(problem_id: str, include_secret: bool = False) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM bug_problems WHERE id = ?", (problem_id,)).fetchone()
    if not row:
        return None
    problem = dict(row)
    problem["hidden_tests"] = json.loads(problem["hidden_tests"])
    problem.pop("initial_tests", None)
    if not include_secret:
        problem.pop("ground_truth_code", None)
        problem.pop("hidden_tests", None)
        problem.pop("llm_code", None)
        problem.pop("reasoning_trace", None)
    problem["active"] = bool(problem["active"])
    return problem


def get_activity_problem(problem_id: str, activity_type: str, include_secret: bool = False) -> dict[str, Any] | None:
    problem = get_bug_problem(problem_id, include_secret=include_secret)
    if not problem or problem.get("activity_type", "bug") != activity_type:
        return None
    return problem


def public_bug_problem(
    problem: dict[str, Any],
    progress: dict[str, Any] | None = None,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = dict(problem)
    legacy_code = str(item.pop("llm_code", ""))
    legacy_reasoning = str(item.pop("reasoning_trace", ""))
    item.pop("ground_truth_code", None)
    item.pop("initial_tests", None)
    item.pop("hidden_tests", None)
    item["active"] = bool(item["active"])
    item["progress"] = progress or {"tests_passed": False, "completed": False}
    if generation:
        item["reasoning_trace"] = generation["reasoning_trace"]
        item["llm_code"] = generation["llm_code"]
        item["generated"] = True
    elif item["progress"].get("tests_passed"):
        # Preserve already-unlocked legacy exercises created before dynamic generation.
        item["reasoning_trace"] = legacy_reasoning
        item["llm_code"] = legacy_code
        item["generated"] = True
    else:
        item["reasoning_trace"] = ""
        item["llm_code"] = ""
        item["generated"] = False
    return item


def get_public_bug_problem(problem_id: str, user_id: int) -> dict[str, Any] | None:
    return next((item for item in list_bug_problems(user_id, activity_type="bug") if item["id"] == problem_id), None)


def latest_bug_generation(user_id: int, problem_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM bug_generations
            WHERE user_id = ? AND problem_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, problem_id),
        ).fetchone()
    return dict(row) if row else None


def record_bug_generation(user_id: int, problem_id: str, reasoning_trace: str, llm_code: str) -> dict[str, Any]:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO bug_generations (user_id, problem_id, reasoning_trace, llm_code, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, problem_id, reasoning_trace, llm_code, iso_now()),
        )
        row = conn.execute("SELECT * FROM bug_generations WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row) if row else {}


def list_human_code_problems(user_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM bug_problems WHERE active = 1 AND activity_type = 'human' ORDER BY position, id"
        ).fetchall()
        completed_rows = conn.execute(
            "SELECT problem_id FROM human_code_submissions WHERE user_id = ? AND passed = 1 GROUP BY problem_id",
            (user_id,),
        ).fetchall()
        completed = {row["problem_id"] for row in completed_rows}
        draft_rows = conn.execute(
            "SELECT problem_id, solution_code, test_code FROM human_code_drafts WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        drafts = {row["problem_id"]: dict(row) for row in draft_rows}
    problems = []
    for row in rows:
        problem = dict(row)
        draft = drafts.get(problem["id"], {})
        starter = _solution_starter(problem["ground_truth_code"], problem["function_name"])
        problems.append({
            "id": problem["id"],
            "title": problem["title"],
            "difficulty": problem["difficulty"],
            "description": problem["description"],
            "function_name": problem["function_name"],
            "position": problem["position"],
            "completed": problem["id"] in completed,
            "solution_code": draft.get("solution_code") or starter,
            "test_code": draft.get("test_code") or "",
        })
    return problems


def save_human_code_draft(user_id: int, problem_id: str, solution_code: str, test_code: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO human_code_drafts (user_id, problem_id, solution_code, test_code, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, problem_id) DO UPDATE SET
                solution_code = excluded.solution_code,
                test_code = excluded.test_code,
                updated_at = excluded.updated_at
            """,
            (user_id, problem_id, solution_code, test_code, iso_now()),
        )


def record_human_code_submission(
    user_id: int,
    problem_id: str,
    solution_code: str,
    passed: bool,
    result: dict[str, Any],
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO human_code_submissions
                (user_id, problem_id, solution_code, passed, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, problem_id, solution_code, int(passed), json.dumps(result), iso_now()),
        )


def _solution_starter(ground_truth_code: str, function_name: str) -> str:
    try:
        tree = ast.parse(ground_truth_code)
        function = next(
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
        )
        names = [argument.arg for argument in function.args.posonlyargs + function.args.args]
        if function.args.vararg:
            names.append("*" + function.args.vararg.arg)
        names.extend(argument.arg for argument in function.args.kwonlyargs)
        if function.args.kwarg:
            names.append("**" + function.args.kwarg.arg)
        return f"def {function_name}({', '.join(names)}):\n    pass\n"
    except (SyntaxError, StopIteration):
        return f"def {function_name}(*args, **kwargs):\n    pass\n"


def save_bug_problem(payload: dict[str, Any]) -> dict[str, Any]:
    problem_id = str(payload.get("id") or "").strip().lower()
    problem_id = "-".join(part for part in "".join(ch if ch.isalnum() else "-" for ch in problem_id).split("-") if part)
    if not problem_id:
        raise ValueError("problem id is required")
    title = str(payload.get("title") or "").strip()
    function_name = str(payload.get("function_name") or "").strip()
    if not title or not function_name or not function_name.isidentifier():
        raise ValueError("title and a valid Python function name are required")
    hidden_tests = payload.get("hidden_tests")
    if isinstance(hidden_tests, str):
        hidden_tests = json.loads(hidden_tests)
    if not isinstance(hidden_tests, list) or not hidden_tests:
        raise ValueError("at least one hidden correction test is required")
    for index, test in enumerate(hidden_tests):
        if not isinstance(test, dict) or "input" not in test or "expected" not in test:
            raise ValueError(f"hidden test {index + 1} must contain input and expected")
        if not isinstance(test["input"], (list, dict)):
            raise ValueError(f"hidden test {index + 1} input must be a positional list or keyword object")
    min_tests = max(1, min(50, int(payload.get("min_student_tests") or 10)))
    activity_type = str(payload.get("activity_type") or "bug").strip().lower()
    if activity_type not in {"bug", "human"}:
        raise ValueError("activity type must be bug or human")
    now = iso_now()
    ground_truth_code = str(payload.get("ground_truth_code") or "")
    if not ground_truth_code.strip():
        raise ValueError("reference solution is required")
    try:
        reference_tree = ast.parse(ground_truth_code, filename="teacher_reference.py")
    except SyntaxError as exc:
        raise ValueError(f"reference solution has invalid Python on line {exc.lineno}: {exc.msg}") from exc
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
        for node in reference_tree.body
    ):
        raise ValueError(f"reference solution must define {function_name}(...)")
    values = {
        "id": problem_id, "activity_type": activity_type, "title": title[:160], "difficulty": str(payload.get("difficulty") or "Easy")[:40],
        "description": str(payload.get("description") or "").strip(), "function_name": function_name,
        "reasoning_trace": str(payload.get("reasoning_trace") or "").strip(),
        "llm_code": str(payload.get("llm_code") or payload.get("ground_truth_code") or ""),
        "ground_truth_code": ground_truth_code,
        "initial_tests": "[]", "hidden_tests": json.dumps(hidden_tests), "min_student_tests": min_tests,
        "position": int(payload.get("position") or 0), "active": int(bool(payload.get("active", True))),
        "created_at": now, "updated_at": now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO bug_problems
                (id, activity_type, title, difficulty, description, function_name, reasoning_trace, llm_code,
                 ground_truth_code, initial_tests, hidden_tests, min_student_tests, position, active, created_at, updated_at)
            VALUES
                (:id, :activity_type, :title, :difficulty, :description, :function_name, :reasoning_trace, :llm_code,
                 :ground_truth_code, :initial_tests, :hidden_tests, :min_student_tests, :position, :active, :created_at, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                activity_type = excluded.activity_type, title = excluded.title, difficulty = excluded.difficulty, description = excluded.description,
                function_name = excluded.function_name, reasoning_trace = excluded.reasoning_trace,
                llm_code = excluded.llm_code, ground_truth_code = excluded.ground_truth_code,
                initial_tests = excluded.initial_tests, hidden_tests = excluded.hidden_tests,
                min_student_tests = excluded.min_student_tests,
                position = excluded.position, active = excluded.active, updated_at = excluded.updated_at
            """,
            values,
        )
    return get_bug_problem(problem_id, include_secret=True) or {}


def latest_passing_bug_tests(user_id: int, problem_id: str) -> str | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT student_tests FROM bug_submissions
            WHERE user_id = ? AND problem_id = ? AND stage = 'tests' AND passed = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, problem_id),
        ).fetchone()
    return str(row["student_tests"]) if row else None


def record_bug_submission(
    user_id: int,
    problem_id: str,
    stage: str,
    test_code: str,
    corrected_code: str,
    result: dict[str, Any],
) -> None:
    if stage not in ("tests", "fix"):
        raise ValueError("invalid bug-lab stage")
    stage_passed = bool(result.get("gate_passed")) if stage == "tests" else bool(result.get("passed"))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO bug_submissions
                (user_id, problem_id, stage, student_tests, corrected_code, passed, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, problem_id, stage, test_code, corrected_code, int(stage_passed), json.dumps(result), iso_now()),
        )


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "must_change_password": bool(user["must_change_password"]),
    }


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
