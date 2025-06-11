import sqlite3
import json
from datetime import datetime

DB_PATH = "memory.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create the table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            filename TEXT,
            file_format TEXT,
            intent TEXT,
            agent_result TEXT,
            action_taken TEXT
        )
    ''')
    
    # Ensure file_type column exists
    c.execute("PRAGMA table_info(memory)")
    columns = [col[1] for col in c.fetchall()]
    if "file_type" not in columns:
        c.execute("ALTER TABLE memory ADD COLUMN file_type TEXT")
    
    conn.commit()
    conn.close()

def insert_agent_trace(filename, file_type, intent, agent_result, action_taken):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('''
        INSERT INTO memory (timestamp, filename, file_type, intent, agent_result, action_taken)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, filename, file_type, intent, json.dumps(agent_result), action_taken))
    conn.commit()
    conn.close()

def get_all_records():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM memory ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

