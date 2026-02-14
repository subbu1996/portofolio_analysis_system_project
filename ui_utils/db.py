import sqlite3
import uuid
from datetime import datetime
import pytz # You might need: pip install pytz

DB_FILE = "chat.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            thinking_process TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

# --- Session Management ---

def create_session(title="New Chat"):
    session_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, title))
    conn.commit()
    conn.close()
    return session_id

def get_all_sessions():
    conn = get_connection()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [dict(s) for s in sessions]

def delete_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_session_title(session_id, new_title):
    conn = get_connection()
    conn.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (new_title, session_id))
    conn.commit()
    conn.close()

# --- Message Management ---

def add_message(session_id, role, content, thinking_process=None):
    conn = get_connection()
    cursor = conn.cursor() 
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, thinking_process) VALUES (?, ?, ?, ?)",
        (session_id, role, content, thinking_process)
    )
    message_id = cursor.lastrowid 
    conn.commit()
    conn.close()
    return message_id 

def update_message_content(message_id, content, thinking_process=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if thinking_process is not None:
        cursor.execute("""
            UPDATE messages 
            SET content = ?, thinking_process = ?
            WHERE id = ?
        """, (content, thinking_process, message_id))
    else:
        cursor.execute("""
            UPDATE messages 
            SET content = ?
            WHERE id = ?
        """, (content, message_id))
    
    conn.commit()
    conn.close()

def get_messages(session_id):
    conn = get_connection()
    msgs = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()
    conn.close()
    return [dict(m) for m in msgs]

init_db()