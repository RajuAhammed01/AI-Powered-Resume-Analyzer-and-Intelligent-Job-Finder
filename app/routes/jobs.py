import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob
from app.services.job_api import fetch_jobs
from app.services.matcher import basic_match_score, tfidf_cosine_score
from app.services.skill_extractor import extract_skills
from app.services.skill_gap import get_skill_gap, suggest_learning

jobs_bp = Blueprint("jobs", __name__)

USER_JOBS_CACHE = {}


@jobs_bp.route("/results")
@login_required
def results():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    if not resume:
        flash("Please upload your resume first so our AI can analyze your skills and find matching jobs.")
        return redirect(url_for("resume.upload"))

    pref = JobPreference.query.filter_by(user_id=current_user.id).first()

    # Create default preference if none exists
    if not pref:
        pref = JobPreference(user_id=current_user.id)
        db.session.add(pref)
        db.session.commit()

    resume_skills = json.loads(resume.extracted_skills or "[]") if resume.extracted_skills else []
    resume_text = resume.extracted_text or ""

    search_query = request.args.get("q", "").strip()
    source_query = request.args.get("source", "all").strip().lower()
    target_role = search_query if search_query else (pref.target_role or "Software Engineer")
    location = pref.location or "Remote"

    jobs = fetch_jobs(target_role, location, source=source_query)
    for index, job in enumerate(jobs):
        description = job.get("job_description", "")
        job_skills = extract_skills(description)
        job["job_skills"] = job_skills
        job["match_score"] = basic_match_score(resume_skills, job_skills)
        job["cosine_score"] = tfidf_cosine_score(resume_text, description)
        job["combined_score"] = int((job["match_score"] + job["cosine_score"]) / 2)
        matched, missing = get_skill_gap(resume_skills, job_skills)
        job["matched_skills"] = matched
        job["missing_skills"] = missing
        job["cache_id"] = index

    jobs.sort(key=lambda j: j.get("combined_score", 0), reverse=True)
    USER_JOBS_CACHE[current_user.id] = jobs[:25]

    saved_jobs_count = SavedJob.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "results.html",
        jobs=jobs[:25],
        resume=resume,
        saved_jobs_count=saved_jobs_count,
        top_match_score=jobs[0]["combined_score"] if jobs else 92,
        selected_source=source_query,
    )


@jobs_bp.route("/job/<int:index>")
@login_required
def job_detail(index):
    jobs = USER_JOBS_CACHE.get(current_user.id, [])
    if 0 <= index < len(jobs):
        job = jobs[index]
        resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
        learning_resources = suggest_learning(job.get("missing_skills", []))
        similar_jobs = [j for i, j in enumerate(jobs) if i != index][:3]
        return render_template(
            "job_detail.html",
            job=job,
            index=index,
            resume=resume,
            learning_resources=learning_resources,
            similar_jobs=similar_jobs,
        )

    flash("Job details not found in cache. Refreshing recommendations.")
    return redirect(url_for("jobs.results"))


@jobs_bp.route("/apply-job", methods=["POST"])
@login_required
def apply_job():
    from datetime import datetime
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    match_score = int(request.form.get("match_score", 85))

    existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
    if existing:
        existing.status = "Applied"
        existing.applied_date = datetime.utcnow()
        if apply_link:
            existing.apply_link = apply_link
    else:
        applied = SavedJob(
            user_id=current_user.id,
            job_title=job_title,
            company=company,
            apply_link=apply_link,
            location=location,
            match_score=match_score,
            status="Applied",
            applied_date=datetime.utcnow(),
        )
        db.session.add(applied)

    db.session.commit()
    flash(f"🎉 Application submitted successfully for {job_title} at {company}! Your profile and resume have been forwarded.")
    return redirect(request.referrer or url_for("jobs.saved_jobs"))


@jobs_bp.route("/saved-jobs")
@login_required
def saved_jobs():
    saved_list = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_date.desc()).all()
    return render_template("saved_jobs.html", saved_jobs=saved_list)


@jobs_bp.route("/save-job", methods=["POST"])
@login_required
def save_job():
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    match_score = int(request.form.get("match_score", 85))

    # Avoid duplicate saves
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
    if not existing:
        saved = SavedJob(
            user_id=current_user.id,
            job_title=job_title,
            company=company,
            apply_link=apply_link,
            location=location,
            match_score=match_score,
        )
        db.session.add(saved)
        db.session.commit()
        flash(f"Saved {job_title} at {company} to your saved jobs!")
    else:
        flash("Job is already saved.")

    return redirect(request.referrer or url_for("jobs.saved_jobs"))


@jobs_bp.route("/remove-saved-job/<int:id>", methods=["POST"])
@login_required
def remove_saved_job(id):
    job = db.session.get(SavedJob, id)
    if job and job.user_id == current_user.id:
        db.session.delete(job)
        db.session.commit()
        flash("Job removed from saved list.")
    return redirect(url_for("jobs.saved_jobs"))
