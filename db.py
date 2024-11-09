import sqlite3

DB_NAME = "user_data.db"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        default_duration INTEGER DEFAULT 60
    )
    """)
    conn.commit()
    conn.close()

# Сохранение учетных данных пользователя
def save_user_credentials(user_id, username, password, default_duration=60):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, password, default_duration) VALUES (?, ?, ?, ?)",
        (user_id, username, password, default_duration)
    )
    conn.commit()
    conn.close()

# Получение учетных данных пользователя
def get_user_credentials(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, default_duration FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Обновление продолжительности по умолчанию
def update_default_duration(user_id, duration):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET default_duration = ? WHERE user_id = ?",
        (duration, user_id)
    )
    conn.commit()
    conn.close()
