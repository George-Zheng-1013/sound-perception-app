import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "audio_results.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT * FROM audio_results ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()