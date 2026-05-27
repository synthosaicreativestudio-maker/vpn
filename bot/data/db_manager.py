"""Менеджер базы данных Telegram-бота.

Хранит информацию о пользователях, платежах и подписках.
"""
import logging
import sqlite3
from datetime import datetime

from bot.config import DB_PATH

logger = logging.getLogger(__name__)


class DBManager:
    def __init__(self):
        self.db_path = DB_PATH
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # ← используем именованные колонки
        return conn

    def _create_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    tg_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscription_expires DATETIME,
                    vless_link TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    has_trial BOOLEAN DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER,
                    order_id TEXT UNIQUE,
                    amount REAL,
                    plan_id TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tg_id) REFERENCES users(tg_id)
                )
            """)
            # Авто-миграция для старых баз
            for alter_sql in [
                "ALTER TABLE users ADD COLUMN has_trial BOOLEAN DEFAULT 0",
                "ALTER TABLE payments ADD COLUMN order_id TEXT UNIQUE",
                "ALTER TABLE payments ADD COLUMN plan_id TEXT",
            ]:
                try:
                    cursor.execute(alter_sql)
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
            conn.commit()

    # ── Users ─────────────────────────────────────────────────

    def add_user(self, tg_id: int, username: str | None):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (tg_id, username) VALUES (?, ?)",
                (tg_id, username),
            )
            conn.commit()

    def update_subscription(self, tg_id: int, expires_at: str, link: str):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE users SET subscription_expires = ?, vless_link = ? WHERE tg_id = ?",
                (expires_at, link, tg_id),
            )
            conn.commit()

    def get_user(self, tg_id: int) -> sqlite3.Row | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
            ).fetchone()
            return row

    def has_user_trial(self, tg_id: int) -> bool:
        user = self.get_user(tg_id)
        if user:
            return bool(user["has_trial"])  # ← именованная колонка, не числовой индекс
        return False

    def set_user_trial(self, tg_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE users SET has_trial = 1 WHERE tg_id = ?", (tg_id,)
            )
            conn.commit()

    def get_users_with_expiring_subscriptions(self, days_before: int) -> list:
        """Получить пользователей, у которых подписка истекает через N дней."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT tg_id, username, subscription_expires, vless_link
                FROM users
                WHERE subscription_expires IS NOT NULL
                  AND subscription_expires != ''
                  AND date(subscription_expires) = date('now', ?)
                """,
                (f"+{days_before} days",),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Payments ──────────────────────────────────────────────

    def order_exists(self, order_id: str) -> bool:
        """Проверить, не обработан ли уже данный заказ (идемпотентность)."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM payments WHERE order_id = ? AND status = 'CONFIRMED'",
                (order_id,),
            ).fetchone()
            return row is not None

    def add_payment(
        self,
        tg_id: int,
        order_id: str,
        amount: float,
        plan_id: str,
        status: str,
    ):
        """Записать платёж в БД."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO payments (tg_id, order_id, amount, plan_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET status = excluded.status
                """,
                (tg_id, order_id, amount, plan_id, status, datetime.utcnow().isoformat()),
            )
            conn.commit()
            logger.info(
                "Payment recorded: order=%s tg_id=%s amount=%.2f plan=%s status=%s",
                order_id,
                tg_id,
                amount,
                plan_id,
                status,
            )
