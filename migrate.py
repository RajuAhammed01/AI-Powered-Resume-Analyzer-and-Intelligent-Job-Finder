import sqlite3
import os

db_path = 'instance/database.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE saved_job ADD COLUMN status VARCHAR(50) DEFAULT 'Saved'")
        print("Added status column")
    except sqlite3.OperationalError as e:
        print(f"Status column may already exist: {e}")
        
    try:
        conn.execute("ALTER TABLE saved_job ADD COLUMN applied_date DATETIME")
        print("Added applied_date column")
    except sqlite3.OperationalError as e:
        print(f"Applied_date column may already exist: {e}")
        
    conn.commit()
    conn.close()
else:
    print("Database not found!")
