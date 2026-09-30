import os
import pathlib

# ── ensure models/ exists so train_ner.py can write there ──────────────────────
pathlib.Path("models").mkdir(exist_ok=True)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
