import sqlite3, re
import os

def clean_db(path='/var/lib/marzban/db.sqlite3'):
    if not os.path.exists(path):
        print(f"DB not found at {path}")
        return

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users")
        for uid, name in cursor.fetchall():
            new_name = re.sub(r'[^a-zA-Z0-9\-_]', '', name)
            if not new_name: new_name = f"user_{uid}"
            if new_name != name:
                print(f"Fixing {name} -> {new_name}")
                cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_name, uid))
        conn.commit()
    print("✅ База данных очищена.")

if __name__ == "__main__":
    clean_db()
