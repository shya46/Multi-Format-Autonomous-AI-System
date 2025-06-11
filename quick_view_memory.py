# quick_view_memory.py
import sqlite3
import json

conn = sqlite3.connect("memory.db")
c = conn.cursor()
c.execute("SELECT * FROM memory")
rows = c.fetchall()

for row in rows:
    print("-----")
    print("ID:", row[0])
    print("Timestamp:", row[1])
    print("Source:", row[2])
    print("Filename:", row[3])
    print("File Format:", row[4])
    print("Intent:", row[5])
    print("Agent Result:", json.loads(row[6]))
    print("Action Taken:", row[7])
conn.close()
