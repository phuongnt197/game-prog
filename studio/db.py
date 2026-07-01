from __future__ import annotations

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
from .config import DATA_DIR


DB_PATH = Path(os.getenv("AIP1_DB_PATH", DATA_DIR / "studio.sqlite3"))
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

            CREATE INDEX IF NOT EXISTS idx_behavior_user_assignment
                ON behavior_events(user_id, assignment_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_user_assignment
                ON submissions(user_id, assignment_id);
            CREATE INDEX IF NOT EXISTS idx_assignment_drafts_user_assignment
                ON assignment_drafts(user_id, assignment_id);
            """
        )
    seed_admin()


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


def can_use_studio(user: dict[str, Any]) -> bool:
    return is_assignment_unlocked(user, "project-studio")


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


def save_project(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "Untitled Project").strip()[:120]
    slug = unique_slug(title)
    now = iso_now()
    creator = str(payload.get("creator") or user.get("display_name") or user.get("username")).strip()[:80]
    project = {
        "slug": slug,
        "user_id": user["id"],
        "title": title,
        "creator": creator,
        "description": str(payload.get("description") or "").strip()[:800],
        "template_id": str(payload.get("template_id") or "adventure"),
        "code": str(payload.get("code") or ""),
        "tests": str(payload.get("tests") or "[]"),
        "specification": str(payload.get("specification") or ""),
        "ai_record": str(payload.get("ai_record") or ""),
        "created_at": now,
        "updated_at": now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO projects
                (slug, user_id, title, creator, description, template_id, code, tests, specification, ai_record, created_at, updated_at)
            VALUES
                (:slug, :user_id, :title, :creator, :description, :template_id, :code, :tests, :specification, :ai_record, :created_at, :updated_at)
            """,
            project,
        )
    return project


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


def unique_slug(title: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-") or "project"
    base = "-".join(part for part in base.split("-") if part)
    with connect() as conn:
        slug = base
        index = 2
        while conn.execute("SELECT 1 FROM projects WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base}-{index}"
            index += 1
        return slug


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "must_change_password": bool(user["must_change_password"]),
        "can_use_studio": can_use_studio(user),
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
