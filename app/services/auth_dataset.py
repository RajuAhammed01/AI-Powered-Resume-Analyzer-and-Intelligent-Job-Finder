"""
JobSnap Authentication & Activity Dataset Service
=================================================
Manages storage, hashmap indexing, activity tracking, and dataset export
for user authentication:
- Tracks signup information with exact timestamps (date & time)
- Securely manages password hashing (PBKDF2/scrypt cryptographic hash mapping)
- Records login activity (successful/failed attempts, IP, user-agent, timestamps)
- Maintains an exportable JSON dataset structured as an email-keyed hashmap
"""

import json
import os
from datetime import datetime
from flask import current_app, request
from app.extensions import db


def _is_writable(path: str) -> bool:
    try:
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return True
    except Exception:
        return False


def get_dataset_storage_path(filename: str = "users_auth_dataset.json") -> str:
    """Return a safe writable path for the auth dataset (falls back to /tmp on serverless)."""
    # Isolate test runs to a temporary test file so real user accounts are never overwritten during tests
    if current_app and current_app.config.get("TESTING") and filename == "users_auth_dataset.json":
        filename = "test_users_auth_dataset.json"

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data")
    
    # Check if data directory is writable (not on read-only serverless FS)
    if os.path.exists(data_dir) and _is_writable(data_dir):
        return os.path.join(data_dir, filename)
    
    # Fallback to /tmp on serverless like Vercel or AWS Lambda
    tmp_dir = "/tmp"
    if os.path.exists(tmp_dir) and os.path.isdir(tmp_dir):
        return os.path.join(tmp_dir, filename)
    
    return os.path.join(data_dir, filename)


def get_client_ip() -> str:
    """Extract client IP handling reverse proxy headers."""
    try:
        if request.headers.get("X-Forwarded-For"):
            return request.headers.get("X-Forwarded-For").split(",")[0].strip()
        return request.remote_addr or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def get_client_user_agent() -> str:
    """Extract client User-Agent string."""
    try:
        return (request.user_agent.string or "")[:250]
    except Exception:
        return "Unknown"


def record_login_activity(
    email: str,
    status: str,
    user=None,
    ip_address: str = None,
    user_agent: str = None,
    failure_reason: str = ""
):
    """
    Record an authentication event in the database, update user metadata (last_login, login_count),
    and synchronize the auth dataset file.
    """
    from app.models import LoginHistory, User, utc_now

    ip = ip_address or get_client_ip()
    ua = user_agent or get_client_user_agent()
    now = utc_now()

    user_obj = user
    if not user_obj and email:
        user_obj = User.query.filter_by(email=email.strip().lower()).first()

    # Create history event
    event = LoginHistory(
        user_id=user_obj.id if user_obj else None,
        email=email.strip().lower() if email else "unknown",
        status=status.upper(),
        ip_address=ip,
        user_agent=ua,
        failure_reason=failure_reason,
        timestamp=now,
    )
    db.session.add(event)

    # If login succeeded, update user date stamps and counts
    if status.upper() == "SUCCESS" and user_obj:
        user_obj.last_login = now
        user_obj.last_login_ip = ip
        user_obj.login_count = (user_obj.login_count or 0) + 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if current_app:
            current_app.logger.error(f"Failed to commit login activity: {e}")

    # Synchronize dataset file asynchronously or safely
    sync_auth_dataset_file()
    return event


def build_auth_hashmap() -> dict:
    """
    Construct an in-memory hashmap of all registered users keyed by email.
    Maps: email -> { user_id, name, email, password_hash, signup_date, last_login_date, login_history, ... }
    """
    from app.models import User

    users = User.query.all()
    auth_hashmap = {}

    for u in users:
        auth_hashmap[u.email.lower()] = u.to_hashmap_record()

    return auth_hashmap


def sync_auth_dataset_file(filepath: str = None) -> bool:
    """
    Export current authentication dataset into a JSON file formatted as an email-indexed hashmap.
    """
    target_path = filepath or get_dataset_storage_path("users_auth_dataset.json")
    try:
        auth_map = build_auth_hashmap()
        dataset_content = {
            "metadata": {
                "dataset_name": "JobSnap User Authentication & Login Activity Dataset",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_users": len(auth_map),
                "storage_type": "email_indexed_hashmap",
                "hash_algorithm": "werkzeug_scrypt_pbkdf2_salted",
            },
            "users_hashmap": auth_map,
        }

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(dataset_content, f, indent=2)
        return True
    except Exception as e:
        if current_app:
            current_app.logger.warning(f"Could not sync auth dataset file: {e}")
        return False


def restore_users_from_auth_dataset() -> int:
    """
    Restore registered users and their password hashes from users_auth_dataset.json into the database
    if they do not already exist (e.g. on fresh instances, serverless /tmp reloads on Vercel, or newly cloned environments).
    """
    from app.models import User, db
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(base_dir, "data", "users_auth_dataset.json")

    if not os.path.exists(dataset_path):
        return 0

    restored_count = 0
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        users_map = data.get("users_hashmap", {})
        for email, u_data in users_map.items():
            clean_email = email.strip().lower()
            existing = User.query.filter_by(email=clean_email).first()
            if not existing and u_data.get("password_hash"):
                created_iso = u_data.get("created_at_iso")
                last_login_iso = u_data.get("last_login_iso")
                created_at = datetime.fromisoformat(created_iso) if created_iso else utc_now()
                last_login = datetime.fromisoformat(last_login_iso) if last_login_iso else None

                user = User(
                    name=u_data.get("name") or clean_email.split("@")[0],
                    email=clean_email,
                    password_hash=u_data.get("password_hash"),
                    created_at=created_at,
                    last_login=last_login,
                    last_login_ip=u_data.get("last_login_ip", ""),
                    login_count=u_data.get("total_logins", 0),
                    status=u_data.get("status", "active"),
                )
                db.session.add(user)
                restored_count += 1

        if restored_count > 0:
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        if current_app:
            current_app.logger.warning(f"Could not restore users from auth dataset: {e}")

    return restored_count


def get_auth_dataset_summary() -> dict:
    """Return statistical summary of authentication dataset."""
    from app.models import LoginHistory, User

    total_users = User.query.count()
    total_logins = LoginHistory.query.count()
    successful_logins = LoginHistory.query.filter_by(status="SUCCESS").count()
    failed_logins = LoginHistory.query.filter_by(status="FAILED").count()

    latest_user = User.query.order_by(User.created_at.desc()).first()
    latest_login = LoginHistory.query.order_by(LoginHistory.timestamp.desc()).first()

    return {
        "total_registered_users": total_users,
        "total_login_attempts": total_logins,
        "successful_logins": successful_logins,
        "failed_logins": failed_logins,
        "latest_signup_date": latest_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if latest_user and latest_user.created_at else "None",
        "latest_login_date": latest_login.timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_login and latest_login.timestamp else "None",
    }


if __name__ == "__main__":
    import sys
    # Backend Command Line Tool for Dataset Management
    from app import create_app
    app = create_app()
    with app.app_context():
        if "--export" in sys.argv:
            path = get_dataset_storage_path("users_auth_dataset.json")
            ok = sync_auth_dataset_file(path)
            print(f"[BACKEND DATASET] Synchronized to: {path} (success={ok})")
        else:
            summary = get_auth_dataset_summary()
            print("[BACKEND DATASET] Authentication & User Stats:")
            for k, v in summary.items():
                print(f"  {k}: {v}")

