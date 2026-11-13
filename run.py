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

    # Command-line overrides
    use_prod = "--prod" in sys.argv or "--production" in sys.argv
    use_dev = "--dev" in sys.argv or "--debug" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]

    # Production mode is default unless FLASK_DEBUG=1 or --dev is passed
    env_debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("true", "1")
    debug = use_dev or (env_debug and not use_prod)

    if not debug:
        try:
            from waitress import serve
            print(f"[*] Starting JobSnap on http://{host}:{port}", flush=True)
            print(f"[*] Production WSGI Server active (Waitress multi-threaded engine).", flush=True)
            print(f"[*] Development server warning resolved: ready for actual developments.", flush=True)
            serve(app, host=host, port=port, threads=8)
            sys.exit(0)
        except ImportError:
            print("[!] Waitress not installed; falling back to Werkzeug development server.", flush=True)

    print(f"[*] Starting JobSnap development server on http://{host}:{port} (debug={debug})", flush=True)
    app.run(host=host, port=port, debug=debug)
