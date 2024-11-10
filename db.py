import sqlite3

DB_NAME = "user_data.db"

# Initialize the database
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        status TEXT DEFAULT 'pending'
    )
    """)
    conn.commit()
    conn.close()

# Save user credentials
def save_user_credentials(user_id, username, password, default_duration=60):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, password, default_duration) VALUES (?, ?, ?, ?)",
        (user_id, username, password, default_duration)
    )
    conn.commit()
    conn.close()

# Get user credentials
def get_user_credentials(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password, default_duration FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Update default duration
def update_default_duration(user_id, duration):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET default_duration = ? WHERE user_id = ?",
        (duration, user_id)
    )
    conn.commit()
    conn.close()

# Get all users
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    result = cursor.fetchall()
    conn.close()
    return result

# Delete a user
def delete_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Update user credentials
def update_user_credentials(user_id, username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET username = ?, password = ? WHERE user_id = ?",
        (username, password, user_id)
    )
    conn.commit()
    conn.close()

# Save user request
def save_user_request(user_id, username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO requests (user_id, username, password) VALUES (?, ?, ?)",
        (user_id, username, password)
    )
    conn.commit()
    conn.close()

# Get all requests
def get_all_requests():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM requests WHERE status = 'pending'")
    result = cursor.fetchall()
    conn.close()
    return result

# Approve user request
def approve_user_request(request_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, password FROM requests WHERE request_id = ?", (request_id,))
    request = cursor.fetchone()
    if request:
        user_id, username, password = request
        save_user_credentials(user_id, username, password)
        cursor.execute("UPDATE requests SET status = 'approved' WHERE request_id = ?", (request_id,))
        conn.commit()
        conn.close()
        return user_id, username
    conn.close()
    return None, None
