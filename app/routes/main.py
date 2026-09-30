from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Resume, SavedJob, User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    saved_jobs = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_date.desc()).all()
    extracted_skills_count = len(resume.skills) if resume and resume.skills else 0
    top_match_score = 92 if resume else 0

    return render_template(
        "dashboard.html",
        resume=resume,
        saved_jobs=saved_jobs,
        extracted_skills_count=extracted_skills_count,
        top_match_score=top_match_score,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "update_profile":
            current_user.name = request.form.get("name", current_user.name).strip()
            current_user.phone = request.form.get("phone", "").strip()
            current_user.location = request.form.get("location", "").strip()
            current_user.title_role = request.form.get("title_role", current_user.title_role).strip()
            current_user.date_of_birth = request.form.get("date_of_birth", "").strip()
            current_user.linkedin_url = request.form.get("linkedin_url", "").strip()
            db.session.commit()
            flash("Profile information updated successfully.")

        elif action == "change_password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pass):
                flash("Current password is incorrect.")
            elif len(new_pass) < 6:
                flash("New password must be at least 6 characters long.")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Password updated successfully.")

        elif action == "update_settings":
            current_user.language = request.form.get("language", "English")
            current_user.theme = request.form.get("theme", "Light")
            current_user.notifications_enabled = request.form.get("notifications_enabled") == "on"
            db.session.commit()
            flash("Settings updated successfully.")

        return redirect(url_for("main.profile"))

    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    return render_template("profile.html", resume=resume)
