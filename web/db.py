"""SQLite: schema e helpers isolados por user_id."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / "data" / "app.db"


def get_db_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(DEFAULT_DB_PATH)))


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                gemini_api_key_encrypted TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                master_profile_md TEXT NOT NULL DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_description TEXT NOT NULL,
                generated_md TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def create_user(email: str, password_hash: str, api_key_encrypted: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, gemini_api_key_encrypted)
            VALUES (?, ?, ?)
            """,
            (email.lower().strip(), password_hash, api_key_encrypted),
        )
        user_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO profiles (user_id, master_profile_md) VALUES (?, ?)",
            (user_id, ""),
        )
        return user_id


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_profile(user_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
        ).fetchone()


def save_profile(user_id: int, master_profile_md: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE profiles
            SET master_profile_md = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (master_profile_md, user_id),
        )


def update_gemini_api_key(user_id: int, encrypted: str) -> None:
    """Atualiza a chave Gemini. String vazia = sem chave cadastrada."""
    with connect() as conn:
        conn.execute(
            """
            UPDATE users
            SET gemini_api_key_encrypted = ?
            WHERE id = ?
            """,
            (encrypted, user_id),
        )


def save_job_resume(user_id: int, job_description: str, generated_md: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_resumes (user_id, job_description, generated_md)
            VALUES (?, ?, ?)
            """,
            (user_id, job_description, generated_md),
        )
        return int(cur.lastrowid)


def get_latest_job_resume(user_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM job_resumes
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()


def list_job_resumes(user_id: int, limit: int = 30) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM job_resumes
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def get_job_resume(user_id: int, resume_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            """
            SELECT * FROM job_resumes
            WHERE user_id = ? AND id = ?
            """,
            (user_id, resume_id),
        ).fetchone()
