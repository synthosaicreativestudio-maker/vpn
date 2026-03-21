"""SQLite-хранилище для пользователей и IP-журнала."""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("panel.db")


class PanelDB:
    """Лёгкое хранилище на SQLite для управления подписками."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email       TEXT PRIMARY KEY,
                    uuid        TEXT NOT NULL UNIQUE,
                    ip_limit    INTEGER DEFAULT 2,
                    sub_token   TEXT NOT NULL UNIQUE,
                    created_at  TEXT NOT NULL,
                    expires_at  TEXT,
                    description TEXT,
                    is_active   INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ip_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    email     TEXT NOT NULL,
                    ip        TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(email, ip)
                )
                """
            )
            conn.commit()
        logger.info("Database initialised at %s", self.db_path)

    # ── CRUD ──────────────────────────────────────────────────

    def add_user(
        self,
        email: str,
        uuid: str,
        ip_limit: int,
        sub_token: str,
        expire_days: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Optional[dict]:
        now = datetime.utcnow().isoformat()
        expires_at = None
        if expire_days:
            expires_at = (
                datetime.utcnow() + timedelta(days=expire_days)
            ).isoformat()

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users
                    (email, uuid, ip_limit, sub_token,
                     created_at, expires_at, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (email, uuid, ip_limit, sub_token, now, expires_at, description),
            )
            conn.commit()
        return self.get_user(email)

    def get_user(self, email: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_token(self, token: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE sub_token = ?", (token,)
            ).fetchone()
            return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_user(self, email: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM users WHERE email = ?", (email,)
            )
            conn.execute("DELETE FROM ip_log WHERE email = ?", (email,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_active = 1"
            ).fetchone()[0]
            return {
                "total_users": total,
                "active_users": active,
                "expired_users": total - active,
            }

    # ── IP Tracking ───────────────────────────────────────────

    def log_ip(self, email: str, ip: str):
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO ip_log (email, ip, last_seen)
                VALUES (?, ?, ?)
                ON CONFLICT(email, ip) DO UPDATE SET last_seen = ?
                """,
                (email, ip, now, now),
            )
            conn.commit()

    def get_active_ips(
        self, email: str, window_minutes: int = 5
    ) -> list[str]:
        cutoff = (
            datetime.utcnow() - timedelta(minutes=window_minutes)
        ).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT ip FROM ip_log WHERE email = ? AND last_seen > ?",
                (email, cutoff),
            ).fetchall()
            return [r["ip"] for r in rows]
