"""
JobSnap - One-Click Application Bootstrapper & Runner
=====================================================
Automates complete startup:
1. Environment & Python verification
2. Dependency checks & auto-installation
3. Directory structure & .env setup
4. Database initialization & schema migrations
5. Port conflict resolution (auto-switches if port is busy)
6. Backend & Frontend server launch
7. Health check & automatic browser opening
8. Graceful shutdown handler
"""

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / "venv"
IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_PIP = VENV_DIR / "Scripts" / "pip.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_PIP = VENV_DIR / "bin" / "pip"


def print_banner():
    banner = r"""
========================================================================
       __       _       ____                    
      / /____  / /_    / __/___   ____ _ ____   
 __  / // __ \/ __ \  _\ \ / __ \/ __ `// __ \  
/ /_/ // /_/ / /_/ / /___// / / / /_/ // /_/ /  
\____/ \____/_.___/      /_/ /_/\__,_// .___/   
                                     /_/        
   AI-Powered Resume Analyzer & Intelligent Job Finder
========================================================================
"""
    print(banner)


def log_step(step_num, total_steps, message):
    print(f"\n[{step_num}/{total_steps}] {message}")


def log_success(message):
    print(f"    [+] {message}")


def log_warn(message):
    print(f"    [!] {message}")


def log_error(message):
    print(f"    [X] {message}")


def find_system_python():
    """Finds a suitable Python 3.10-3.12 executable if venv is missing."""
    candidates = []
    if IS_WINDOWS:
        # Check py launcher versions
        for ver in ["-3.12", "-3.11", "-3.10", "-3"]:
            try:
                res = subprocess.run(
                    ["py", ver, "-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                path = res.stdout.strip()
                if path and Path(path).exists():
                    candidates.append(path)
            except Exception:
                pass

    candidates.append(sys.executable)

    for py in candidates:
        try:
            res = subprocess.run(
                [py, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True,
                text=True,
                check=True,
            )
            v_str = res.stdout.strip()
            # Prefer <= 3.12 for spaCy / native C++ wheels compatibility
            major, minor = map(int, v_str.split("."))
            if major == 3 and minor <= 12:
                return py
        except Exception:
            continue

    return candidates[0] if candidates else sys.executable


def verify_python_and_venv():
    """Ensures a functional virtual environment exists."""
    log_step(1, 6, "Verifying Python & Virtual Environment...")

    if VENV_PYTHON.exists():
        log_success(f"Virtual environment active: {VENV_PYTHON}")
        return VENV_PYTHON

    log_warn("Virtual environment not detected. Creating one now...")
    sys_py = find_system_python()
    log_success(f"Using host Python: {sys_py}")

    try:
        subprocess.run([sys_py, "-m", "venv", str(VENV_DIR)], check=True)
        log_success("Created virtual environment in ./venv")
    except Exception as e:
        log_error(f"Failed to create virtual environment: {e}")
        log_warn("Falling back to host Python environment.")
        return sys_py

    return VENV_PYTHON if VENV_PYTHON.exists() else sys_py


def verify_dependencies(python_bin):
    """Verifies that all required packages are installed, installing if missing."""
    log_step(2, 6, "Checking dependencies & required packages...")

    critical_packages = [
        ("flask", "Flask"),
        ("flask_login", "Flask-Login"),
        ("flask_sqlalchemy", "Flask-SQLAlchemy"),
        ("flask_wtf", "Flask-WTF"),
        ("dotenv", "python-dotenv"),
        ("requests", "requests"),
        ("bs4", "beautifulsoup4"),
        ("sklearn", "scikit-learn"),
        ("spacy", "spacy"),
    ]

    missing = []
    check_code = (
        "import sys\n"
        "mods = ['flask', 'flask_login', 'flask_sqlalchemy', 'flask_wtf', 'dotenv', 'requests', 'bs4', 'sklearn', 'spacy']\n"
        "missing = []\n"
        "for m in mods:\n"
        "    try:\n"
        "        __import__(m)\n"
        "    except ImportError:\n"
        "        missing.append(m)\n"
        "print(','.join(missing))\n"
    )

    try:
        res = subprocess.run([str(python_bin), "-c", check_code], capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        if out:
            missing = [p.strip() for p in out.split(",") if p.strip()]
    except Exception as e:
        log_warn(f"Fast dependency check skipped ({e}), checking packages...")
        missing = ["core packages"]

    if not missing:
        log_success("All core dependencies are installed and verified.")
        return True

    log_warn(f"Missing dependencies detected: {', '.join(missing)}")
    log_step("2b", 6, "Installing required packages from requirements.txt...")

    # Ensure pip is present before running pip install
    try:
        subprocess.run([str(python_bin), "-m", "ensurepip", "--default-pip"], capture_output=True)
    except Exception:
        pass

    req_file = BASE_DIR / "requirements.txt"
    pip_cmd = [str(python_bin), "-m", "pip", "install", "-r", str(req_file)]

    try:
        subprocess.run(pip_cmd, check=True)
        log_success("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to install dependencies: {e}")
        log_warn("Attempting to proceed anyway with installed packages...")
        return False


def configure_environment():
    """Sets up required folders, .env configuration, and instance data."""
    log_step(3, 6, "Configuring environment & directories...")

    # Ensure required directories
    for folder in ["instance", "models", "uploads", "data"]:
        (BASE_DIR / folder).mkdir(exist_ok=True)
    log_success("Storage directories verified (uploads/, instance/, models/, data/).")

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        secret_key = secrets.token_hex(24)
        default_env = f"""# JobSnap Environment Configuration
SECRET_KEY={secret_key}
FLASK_APP=run.py
FLASK_DEBUG=0
PORT=5000
HOST=127.0.0.1
"""
        env_path.write_text(default_env, encoding="utf-8")
        log_success("Generated fresh .env configuration with cryptographically secure SECRET_KEY.")
    else:
        log_success(".env configuration file is present.")


def setup_database(python_bin):
    """Initializes tables and runs migrations safely."""
    log_step(4, 6, "Verifying database schema and migrations...")

    db_setup_code = """
import os
from app import create_app
from app.extensions import db
import sqlite3

app = create_app()
with app.app_context():
    db.create_all()

# Ensure migration columns in saved_job table
db_path = os.path.join(app.instance_path, 'database.db')
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(saved_job)")
    columns = [col[1] for col in cur.fetchall()]
    
    if 'status' not in columns:
        conn.execute("ALTER TABLE saved_job ADD COLUMN status VARCHAR(50) DEFAULT 'Saved'")
    if 'applied_date' not in columns:
        conn.execute("ALTER TABLE saved_job ADD COLUMN applied_date DATETIME")
    conn.commit()
    conn.close()

print("DB_OK")
"""
    try:
        res = subprocess.run([str(python_bin), "-c", db_setup_code], capture_output=True, text=True, check=True)
        if "DB_OK" in res.stdout:
            log_success("Database initialized and schema verified.")
            return True
        else:
            log_warn(f"Database setup notice: {res.stdout.strip()}")
            return True
    except Exception as e:
        log_warn(f"Database check warning (non-fatal): {e}")
        return True


def is_port_in_use(port, host="127.0.0.1"):
    """Checks whether a port is currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def resolve_port(preferred_port=5000, host="127.0.0.1"):
    """
    Checks if preferred_port is available.
    If occupied, automatically finds the next available port to prevent collisions.
    """
    log_step(5, 6, f"Checking port availability ({host}:{preferred_port})...")

    if not is_port_in_use(preferred_port, host):
        log_success(f"Port {preferred_port} is available.")
        return preferred_port

    log_warn(f"Port {preferred_port} is already in use by another application or background process.")
    
    # Check if existing process is an already running JobSnap instance
    try:
        url = f"http://{host}:{preferred_port}"
        req = urllib.request.Request(url, headers={"User-Agent": "JobSnapHealthCheck"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                log_warn(f"An active web service is responding on port {preferred_port}.")
    except Exception:
        pass

    # Find next open port
    for candidate in range(preferred_port + 1, preferred_port + 25):
        if not is_port_in_use(candidate, host):
            log_success(f"Automatically selected available port: {candidate} (No conflict).")
            return candidate

    # Fallback to random free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        fallback_port = s.getsockname()[1]
        log_success(f"Selected system-assigned port: {fallback_port}")
        return fallback_port


def wait_and_open_browser(url, timeout_sec=15.0):
    """Polls the server until responding, then opens the user's default browser."""
    start_time = time.time()
    opened = False

    while time.time() - start_time < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JobSnapBootstrapper"})
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status in (200, 302):
                    log_success(f"JobSnap server is alive and responding (HTTP {response.status}).")
                    time.sleep(0.5)
                    log_success(f"Opening default browser at: {url}")
                    webbrowser.open(url)
                    opened = True
                    break
        except Exception:
            time.sleep(0.3)

    if not opened:
        log_warn(f"Browser auto-open timed out. Please open your browser manually at: {url}")


def main():
    print_banner()

    try:
        # Step 1: Python & Venv
        python_bin = verify_python_and_venv()

        # Step 2: Dependencies
        verify_dependencies(python_bin)

        # Step 3: Directories & Environment
        configure_environment()

        # Step 4: Database & Migrations
        setup_database(python_bin)

        # Step 5: Port conflict resolution
        port = resolve_port(preferred_port=5000, host="127.0.0.1")
        host = "127.0.0.1"
        app_url = f"http://{host}:{port}"

        # Step 6: Start Server
        log_step(6, 6, f"Starting JobSnap backend and frontend on {app_url}...")
        
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = host

        server_cmd = [str(python_bin), str(BASE_DIR / "run.py"), "--port", str(port), "--host", host]
        
        print("\n" + "=" * 72)
        print(f"  JobSnap is launching at: {app_url}")
        print("  Press CTRL+C anytime in this window to stop the server cleanly.")
        print("=" * 72 + "\n")

        # Launch server process
        server_process = subprocess.Popen(server_cmd, env=env)

        # Open browser once server is responsive (in separate thread/polling)
        wait_and_open_browser(app_url)

        # Wait on server process
        server_process.wait()

    except KeyboardInterrupt:
        print("\n\n[!] Shutdown requested by user (Ctrl+C). Stopping JobSnap cleanly...")
        try:
            server_process.terminate()
            server_process.wait(timeout=3)
        except Exception:
            try:
                server_process.kill()
            except Exception:
                pass
        print("[+] JobSnap server stopped. Have a great day!")
        sys.exit(0)
    except Exception as e:
        log_error(f"Startup error encountered: {e}")
        import traceback
        traceback.print_exc()
        print("\n[!] Please review the error above. Press Enter to exit.")
        input()
        sys.exit(1)


if __name__ == "__main__":
    main()
