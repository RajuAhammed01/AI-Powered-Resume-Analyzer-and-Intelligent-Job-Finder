import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob
from app.services.job_api import fetch_jobs
from app.services.matcher import basic_match_score, tfidf_cosine_score

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/results")
@login_required
def results():
	resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
	pref = JobPreference.query.filter_by(user_id=current_user.id).first()
	if not resume or not pref:
		flash("Upload a resume and set preferences first")
		return redirect(url_for("resume.upload"))

	resume_skills = json.loads(resume.extracted_skills or "[]")
	jobs = fetch_jobs(pref.target_role, pref.location)
	for job in jobs:
		description = job.get("job_description", "")
		job_skills = [skill.lower() for skill in resume_skills]
		job["match_score"] = basic_match_score(resume_skills, job_skills)
		job["cosine_score"] = tfidf_cosine_score(resume.extracted_text or "", description)
	jobs.sort(key=lambda job: job["match_score"], reverse=True)
	return render_template("results.html", jobs=jobs[:20])


@jobs_bp.route("/job/<int:index>")
@login_required
def job_detail(index):
	return render_template("job_detail.html", job=None, index=index)


@jobs_bp.route("/save-job", methods=["POST"])
@login_required
def save_job():
	job = SavedJob(
		user_id=current_user.id,
		job_title=request.form.get("job_title", ""),
		company=request.form.get("company", ""),
		apply_link=request.form.get("apply_link", ""),
	)
	db.session.add(job)
	db.session.commit()
	flash("Job saved")
	return redirect(url_for("jobs.results"))
