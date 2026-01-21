import sqlite3
import re
import os

def clean_name(text):
    if not text:
        return ""
    # Удаляем эмодзи и спецсимволы, оставляем буквы, цифры и дефис
    # [^a-zA-Z0-9\-] -> заменяем всё, что НЕ буквы/цифры/дефис, на пустоту
    return re.sub(r'[^a-zA-Z0-9\-]', '', text)

def fix_marzban_db(db_path='/var/lib/marzban/db.sqlite3'):
    if not os.path.exists(db_path):
        print(f"❌ Ошибка: Файл БД не найден по пути {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Очистка имен узлов
        cursor.execute("SELECT id, name FROM nodes")
        nodes = cursor.fetchall()
        for node_id, name in nodes:
            new_name = clean_name(name) or f"Node-{node_id}"
            if new_name != name:
                cursor.execute("UPDATE nodes SET name = ? WHERE id = ?", (new_name, node_id))
                print(f"  - Узел {node_id}: '{name}' -> '{new_name}'")

        # Очистка имен пользователей
        cursor.execute("SELECT id, username FROM users")
        users = cursor.fetchall()
        for user_id, username in users:
            new_name = clean_name(username)
            if not new_name:
                # Если после очистки пусто, добавим префикс
                new_name = f"user-{user_id}"
            
            if new_name != username:
                cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_name, user_id))
                print(f"  - Пользователь {user_id}: '{username}' -> '{new_name}'")

        conn.commit()
        conn.close()
        print("✅ База данных нормализована: спецсимволы удалены.")
    except Exception as e:
        print(f"❌ Произошла ошибка при работе с БД: {e}")

if __name__ == "__main__":
    # Для теста можно использовать локальный путь или стандартный путь Marzban
    # fix_marzban_db('db.sqlite3')
    fix_marzban_db()
