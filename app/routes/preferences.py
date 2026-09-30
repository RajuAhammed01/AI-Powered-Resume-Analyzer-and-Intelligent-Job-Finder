import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference

preferences_bp = Blueprint("preferences", __name__)


@preferences_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    pref = JobPreference.query.filter_by(user_id=current_user.id).first()
    if pref is None:
        pref = JobPreference(user_id=current_user.id)
        db.session.add(pref)
        db.session.commit()

    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "reset":
            pref.target_role = "Machine Learning Engineer, Data Scientist"
            pref.location_preference = "Any Location"
            pref.location = "Remote"
            pref.experience_level = "Entry Level (0-1 years)"
            pref.expected_salary = "Any"
            pref.job_type = "Full-time"
            pref.preferred_skills = json.dumps(["Python", "TensorFlow", "scikit-learn", "SQL"])
            db.session.commit()
            flash("Preferences reset to default.")
            return redirect(url_for("preferences.preferences"))

        pref.target_role = request.form.get("target_role", "Machine Learning Engineer, Data Scientist").strip()
        pref.location_preference = request.form.get("location_preference", "Any Location")
        pref.location = request.form.get("location", "Remote").strip()
        pref.experience_level = request.form.get("experience_level", "Entry Level (0-1 years)")
        pref.expected_salary = request.form.get("expected_salary", "Any")
        pref.job_type = request.form.get("job_type", "Full-time")

        skills_raw = request.form.get("preferred_skills", "")
        if skills_raw:
            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            pref.preferred_skills = json.dumps(skills_list)

        db.session.commit()
        flash("Job preferences saved successfully.")
        return redirect(url_for("jobs.results"))

    return render_template("preferences.html", pref=pref)
