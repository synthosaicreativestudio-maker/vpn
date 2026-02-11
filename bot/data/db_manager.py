import sqlite3
import logging
from bot.config import DB_PATH

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        self.db_path = DB_PATH
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    tg_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscription_expires DATETIME,
                    vless_link TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER,
                    amount REAL,
                    tariff TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tg_id) REFERENCES users(tg_id)
                )
            ''')
            conn.commit()

    def add_user(self, tg_id, username):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO users (tg_id, username) VALUES (?, ?)',
                (tg_id, username)
            )
            conn.commit()

    def update_subscription(self, tg_id, expires_at, link):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET subscription_expires = ?, vless_link = ? WHERE tg_id = ?',
                (expires_at, link, tg_id)
            )
            conn.commit()

    def get_user(self, tg_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
            return cursor.fetchone()
