import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _resolve_database_uri() -> str:
    # Check for cloud database URLs (Supabase, Neon, Neon Postgres, Vercel Postgres, Railway)
    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
        or os.getenv("POSTGRES_URL_NON_POOLING")
    )
    if db_url:
        # SQLAlchemy 1.4+ / 2.0+ requires postgresql:// instead of postgres://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    # Serverless fallback (Vercel filesystem is read-only except /tmp)
    if IS_VERCEL:
        return "sqlite:////tmp/database.db"

    # Local development SQLite
    instance_path = os.path.join(BASE_DIR, "instance")
    try:
        os.makedirs(instance_path, exist_ok=True)
    except Exception:
        pass
    return f"sqlite:///{os.path.join(instance_path, 'database.db')}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "jobsnap-dev-production-secret-key-2026")
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD = True

    # Upload folder: /tmp/uploads on Vercel, ./uploads locally
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/uploads" if IS_VERCEL else os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit

    # Enable heavy transformers only if explicitly configured (Sentence-BERT vs TF-IDF)
    ENABLE_HEAVY_TRANSFORMERS = os.getenv("ENABLE_HEAVY_TRANSFORMERS", "false").lower() in ("true", "1")
