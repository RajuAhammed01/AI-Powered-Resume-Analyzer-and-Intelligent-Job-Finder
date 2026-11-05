# JobSnap AI — Resume Analyzer and Intelligent Job Finder

JobSnap is an AI-powered Flask application that extracts verified skills from resumes, performs transparent 3-tier skill gap analysis, fetches real-time jobs from live market APIs, and connects candidates directly to original application portals.

---

## ⚡ One-Click Run & Start

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

## 🔒 Security & Architecture Notes

- **Verified Skill Extraction:** Skills are strictly extracted from CV text without assuming unmentioned technologies (e.g., "Computer Vision").
- **Transparent Match Scoring:** Formula: $\text{Final Score} = 0.60 \times \text{Skill Coverage} + 0.40 \times \text{Semantic Fit}$.
- **3-Tier Competency Breakdown:** Every job displays Matched (100%), Partially Matched (50%, with foundation skill), and Missing (0%) skills.
- **Direct Live Apply:** Redirects users directly to original job application URLs with pipeline tracking.
- Passwords use Werkzeug hashes with CSRF protection enabled across all forms.
