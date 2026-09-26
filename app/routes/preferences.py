from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference

preferences_bp = Blueprint("preferences", __name__)


@preferences_bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
	pref = JobPreference.query.filter_by(user_id=current_user.id).first()
	if request.method == "POST":
		if pref is None:
			pref = JobPreference(user_id=current_user.id)
			db.session.add(pref)
		pref.target_role = request.form.get("target_role", "").strip()
		pref.location = request.form.get("location", "").strip()
		pref.expected_salary = request.form.get("expected_salary", "").strip()
		db.session.commit()
		flash("Preferences saved")
		return redirect(url_for("jobs.results"))

	return render_template("preferences.html", pref=pref)
