from datetime import datetime
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, Response
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import LoginHistory, User, utc_now
from app.services.auth_dataset import (
    build_auth_hashmap,
    get_auth_dataset_summary,
    get_client_ip,
    get_client_user_agent,
    record_login_activity,
    sync_auth_dataset_file,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect(url_for("auth.register"))

        user = User(
            name=name,
            email=email,
            created_at=utc_now(),
            status="active",
        )
        # Hash password securely using werkzeug (scrypt/pbkdf2 hashmap)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Record registration in authentication dataset & audit history
        record_login_activity(
            email=email,
            status="SUCCESS",
            user=user,
            failure_reason="Account registration created",
        )

        flash("Registered successfully! Your account details and secure hash have been stored. Please login.")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", is_auth_page=True)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        from sqlalchemy import func
        identifier = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        # Support sign-in by registered Email OR Username/Name (case-insensitive)
        user = User.query.filter(
            (func.lower(User.email) == identifier.lower()) |
            (func.lower(User.name) == identifier.lower())
        ).first()

        # Verify password (including whitespace-tolerant check for copy-paste safety)
        password_valid = False
        if user:
            if user.check_password(password):
                password_valid = True
            elif password != password.strip() and user.check_password(password.strip()):
                password_valid = True

        if user and password_valid:
            # Record successful login date and client details
            record_login_activity(
                email=user.email,
                status="SUCCESS",
                user=user,
                failure_reason="",
            )
            login_user(user, remember=remember)
            return redirect(url_for("main.dashboard"))

        # Record failed login attempt in dataset for security auditing
        reason = "Invalid password" if user else "Account not registered"
        record_login_activity(
            email=user.email if user else identifier,
            status="FAILED",
            user=user,
            failure_reason=reason,
        )

        flash("Invalid email/username or password")

    return render_template("auth/login.html", is_auth_page=True)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth_bp.route("/activity")
@login_required
def activity():
    """View personal login activity history with dates, IP, and status."""
    logs = (
        LoginHistory.query.filter_by(user_id=current_user.id)
        .order_by(LoginHistory.timestamp.desc())
        .limit(50)
        .all()
    )
    return render_template("auth/activity.html", logs=logs)


@auth_bp.route("/export-my-data")
@login_required
def export_my_data():
    """Download the authenticated user's own profile and activity records (privacy-preserving)."""
    import json
    data = {
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "location": current_user.location,
        "title_role": current_user.title_role,
        "account_created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login.isoformat() if current_user.last_login else None,
        "total_logins": current_user.login_count or 1,
        "login_activity": [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "status": log.status,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
            for log in current_user.login_history[:20]
        ],
    }
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=my_jobsnap_data_{current_user.id}.json"},
    )


@auth_bp.route("/dataset")
@login_required
def dataset_view():
    """
    Returns the user authentication dataset structured as a hashmap
    indexed by email, containing signup date, hashed passwords, and login history.
    """
    hashmap = build_auth_hashmap()
    summary = get_auth_dataset_summary()
    
    # If JSON requested via query arg e.g. /dataset?format=json
    if request.args.get("format") == "json":
        return jsonify({
            "summary": summary,
            "users_hashmap": hashmap,
        })

    return render_template("auth/dataset_view.html", hashmap=hashmap, summary=summary)


@auth_bp.route("/export-dataset")
@login_required
def export_dataset():
    """Download the full authentication & activity dataset as a JSON file."""
    import json
    hashmap = build_auth_hashmap()
    summary = get_auth_dataset_summary()
    data = {
        "dataset_name": "JobSnap User Authentication & Login History Dataset",
        "description": "User credentials (cryptographically hashed), signup dates, and login activity records",
        "exported_at": utc_now().isoformat(),
        "summary": summary,
        "users_hashmap": hashmap,
    }
    response_json = json.dumps(data, indent=2)
    return Response(
        response_json,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=users_auth_dataset.json"},
    )
