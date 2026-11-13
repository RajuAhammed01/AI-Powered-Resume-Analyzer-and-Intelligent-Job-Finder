# JobSnap AI — Resume Analyzer and Intelligent Job Finder

JobSnap is an AI-powered Flask application that extracts verified skills from resumes, performs transparent 3-tier skill gap analysis, fetches real-time jobs from live market APIs, and connects candidates directly to original application portals.

---

## ⚡ One-Click Run & Start

Most Easy: Open terminal and paste: `.\venv\Scripts\python.exe start_app.py`

No manual terminal commands or environment configuration needed! You can launch JobSnap in **one click** using any of the options below:

### Option 1: Double-Click Launcher (Windows Batch)
- Simply double-click **`start.bat`** (or **`run.bat`**) in the project folder.
- **What it does automatically:**
  1. Detects or creates the Python virtual environment (`venv`).
  2. Verifies and installs all required dependencies from `requirements.txt`.
  3. Configures `.env` and directory paths (`uploads/`, `instance/`, `models/`).
  4. Initializes SQLite database tables and schema migrations.
  5. Checks port availability: if port 5000 is occupied, it **automatically routes to an available port (e.g. 5001)** to prevent port conflicts.
  6. Starts the backend & frontend server and **automatically opens your default browser**.

### Option 2: Desktop GUI Launcher (With Clickable "Start" Button)
- Double-click **`JobSnap_GUI.bat`** (or run `python launcher.py`).
- Opens a desktop window featuring:
  - Prominent **`[ ▶ One-Click Start JobSnap ]`** button.
  - Real-time diagnostic badges (Python, Dependencies, Port, Server State).
  - Built-in live activity console with timestamps.
  - One-click **Stop Server** and **Open in Browser** controls.
  - Automatic port collision detection & graceful error handling.

### Option 3: In VS Code / Antigravity IDE
- Open the **Run & Debug** panel (Ctrl+Shift+D) and click the green **▶ Run JobSnap (One-Click Start)** button, or simply press **`F5`**.

---

## 🛠 Manual Command-Line Startup (Optional)

If you prefer running commands manually in PowerShell:

```powershell
# 1. Activate Virtual Environment
.\venv\Scripts\Activate.ps1

# 2. Run the bootstrapper
python start_app.py

# Or launch directly with Flask
python run.py
```

---

## 🧪 Automated Tests

Run the full automated test suite:

```powershell
.\venv\Scripts\python.exe -m pytest
```

---

## 🔒 Security, Authentication Dataset & Architecture

- **User Authentication & Activity Dataset:**
  - **Signup Information & Dates:** Tracks exact registration timestamps (`created_at`) and dates for every user.
  - **Cryptographic Password Hashing:** Uses salted PBKDF2/scrypt cryptographic one-way hashing; passwords are never stored in plain text.
  - **Login Dates & Session Auditing:** Records last login date (`last_login`), client IP address (`last_login_ip`), and cumulative login count.
  - **Email-Indexed Hashmap Dataset:** Structured dataset accessible at `/dataset` and exportable at `/export-dataset` mapping `email -> {user_id, name, password_hash, signup_date, last_login_date, total_logins, login_history}`.
  - **Audit Trail (`LoginHistory`):** Logs every successful and failed login attempt with timestamp, IP, User-Agent, and status.

- **Verified Skill Extraction:** Skills are strictly extracted from CV text without assuming unmentioned technologies (e.g., "Computer Vision").
- **Transparent Match Scoring:** Formula: $\text{Final Score} = 0.60 \times \text{Skill Coverage} + 0.40 \times \text{Semantic Fit}$.
- **3-Tier Competency Breakdown:** Every job displays Matched (100%), Partially Matched (50%, with foundation skill), and Missing (0%) skills.
- **Direct Live Apply:** Redirects users directly to original job application URLs with pipeline tracking.
- Passwords use Werkzeug hashes with CSRF protection enabled across all forms.

---

## 🚀 Deploy to Vercel (Production)

JobSnap is fully configured for deployment on Vercel:

1. **Vercel Config:** Configured in `vercel.json` and WSGI entrypoint `api/index.py`.
2. **Serverless Optimized:** Lightweight production dependencies in `requirements.txt` (< 250MB size limit) with pure-Python PostgreSQL driver `pg8000`.
3. **Database Support:** Automatic support for external cloud databases via `DATABASE_URL` (Neon, Supabase, Vercel Postgres) with graceful fallback to `/tmp/database.db`.
4. **Deploy Command:**
   ```bash
   vercel --prod
   ```

For detailed setup instructions, see the complete guide: [VERCEL_DEPLOYMENT.md](file:///e:/JobSnap/AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder/VERCEL_DEPLOYMENT.md).
