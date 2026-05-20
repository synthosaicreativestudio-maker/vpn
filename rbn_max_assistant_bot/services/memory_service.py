import sqlite3
import logging

logger = logging.getLogger(__name__)

class MemoryService:
    """Сервис долгосрочной памяти разговоров на базе SQLite."""

    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Создает таблицу сообщений и индексы."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        role TEXT,
                        content TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON messages (user_id)")
                logger.info("MemoryService: БД SQLite инициализирована.")
        except Exception as e:
            logger.error("MemoryService: Ошибка инициализации БД: %s", e)

    def add_message(self, user_id: int, role: str, content: str):
        """Добавляет сообщение в историю и удаляет старые (лимит 20 на пользователя)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                    (user_id, role, content)
                )
                # Очистка старых сообщений: оставляем только последние 20 для этого пользователя
                conn.execute("""
                    DELETE FROM messages 
                    WHERE user_id = ? AND id NOT IN (
                        SELECT id FROM messages 
                        WHERE user_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 20
                    )
                """, (user_id, user_id))
        except Exception as e:
            logger.error("MemoryService: Ошибка при сохранении сообщения: %s", e)

    def get_history(self, user_id: int, limit: int = 20) -> list[dict]:
        """Возвращает историю сообщений для формирования контекста LLM."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (user_id, limit)
                )
                return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
        except Exception as e:
            logger.error("MemoryService: Ошибка при получении истории: %s", e)
            return []

    def clear_history(self, user_id: int):
        """Полная очистка памяти пользователя."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        except Exception as e:
            logger.error("MemoryService: Ошибка при очистке истории: %s", e)

memory_service = MemoryService()
