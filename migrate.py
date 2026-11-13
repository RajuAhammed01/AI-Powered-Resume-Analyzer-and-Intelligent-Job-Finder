import os
import sqlite3

db_path = "instance/database.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure saved_job columns
    cur.execute("PRAGMA table_info(saved_job)")
    saved_cols = [c[1] for c in cur.fetchall()]
    if "status" not in saved_cols:
        conn.execute("ALTER TABLE saved_job ADD COLUMN status VARCHAR(50) DEFAULT 'Saved'")
        print("[+] Added status column to saved_job")
    if "applied_date" not in saved_cols:
        conn.execute("ALTER TABLE saved_job ADD COLUMN applied_date DATETIME")
        print("[+] Added applied_date column to saved_job")

    # Ensure user columns
    cur.execute("PRAGMA table_info(user)")
    user_cols = [c[1] for c in cur.fetchall()]
    if "last_login" not in user_cols:
        conn.execute("ALTER TABLE user ADD COLUMN last_login DATETIME")
        print("[+] Added last_login column to user")
    if "last_login_ip" not in user_cols:
        conn.execute("ALTER TABLE user ADD COLUMN last_login_ip VARCHAR(45) DEFAULT ''")
        print("[+] Added last_login_ip column to user")
    if "login_count" not in user_cols:
        conn.execute("ALTER TABLE user ADD COLUMN login_count INTEGER DEFAULT 0")
        print("[+] Added login_count column to user")
    if "status" not in user_cols:
        conn.execute("ALTER TABLE user ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
        print("[+] Added status column to user")

    conn.commit()
    conn.close()
    print("[*] Migration completed successfully.")
else:
    print("[!] Database not found at instance/database.db")
