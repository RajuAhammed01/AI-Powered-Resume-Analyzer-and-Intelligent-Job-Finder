import os
import pathlib
import sys

# ── Ensure required directories exist if filesystem is writable ────────────────
try:
    pathlib.Path("models").mkdir(exist_ok=True)
    pathlib.Path("uploads").mkdir(exist_ok=True)
    pathlib.Path("instance").mkdir(exist_ok=True)
except Exception:
    pass

from app import create_app

# Vercel and WSGI entry point: exposes Flask application as 'app'
app = create_app()

if __name__ == "__main__":
    # Support dynamic PORT and HOST to prevent port collisions
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")

    # Command-line override: python run.py --port 5001
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]

    print(f"[*] Starting JobSnap server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
