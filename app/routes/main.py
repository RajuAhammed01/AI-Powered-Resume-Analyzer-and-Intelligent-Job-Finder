from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob, User
from app.routes.jobs import USER_JOBS_CACHE
from app.services.job_api import fetch_jobs
from app.services.matcher import basic_match_score, tfidf_cosine_score
from app.services.resume_parser import extract_structure
from app.services.skill_extractor import extract_skills
from app.services.skill_gap import get_skill_gap

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

    recommended_jobs = []
    top_match_score = None
    skill_gap_summary = []

    if resume:
        pref = JobPreference.query.filter_by(user_id=current_user.id).first()
        target_role = (pref.target_role if pref else None) or "Software Engineer"
        location = (pref.location if pref else None) or "Remote"

        resume_skills = resume.skills or []
        resume_text = resume.extracted_text or ""

        raw_jobs = fetch_jobs(target_role, location)
        processed_jobs = []
        for index, job_item in enumerate(raw_jobs):
            job = dict(job_item)
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
            processed_jobs.append(job)

        processed_jobs.sort(key=lambda j: j.get("combined_score", 0), reverse=True)
        USER_JOBS_CACHE[current_user.id] = processed_jobs[:20]
        recommended_jobs = processed_jobs[:3]

        if recommended_jobs:
            top_match_score = recommended_jobs[0]["combined_score"]

        # Aggregate missing skills from recommended jobs
        missing_skills_map = {}
        for j in processed_jobs[:5]:
            for s in j.get("missing_skills", []):
                missing_skills_map[s] = missing_skills_map.get(s, 0) + 1

        top_missing_sorted = sorted(missing_skills_map.items(), key=lambda x: x[1], reverse=True)[:5]
        demand_weights = [88, 80, 75, 70, 65]
        for idx, (skill_name, _) in enumerate(top_missing_sorted):
            weight = demand_weights[idx] if idx < len(demand_weights) else 60
            level = "High demand" if weight >= 80 else "Medium demand"
            color = "#ef4444" if weight >= 80 else "#f59e0b"
            skill_gap_summary.append({
                "skill": skill_name,
                "demand": weight,
                "level": level,
                "color": color
            })

    pipeline_stats = {
        "saved": len([j for j in saved_jobs if (j.status or 'Saved').lower() == 'saved']),
        "applied": len([j for j in saved_jobs if (j.status or '').lower() == 'applied']),
        "interview": len([j for j in saved_jobs if (j.status or '').lower() == 'interview']),
        "offer": len([j for j in saved_jobs if (j.status or '').lower() == 'offer']),
        "total": len(saved_jobs)
    }

    return render_template(
        "dashboard.html",
        resume=resume,
        saved_jobs=saved_jobs,
        extracted_skills_count=extracted_skills_count,
        top_match_score=top_match_score,
        recommended_jobs=recommended_jobs,
        skill_gap_summary=skill_gap_summary,
        pipeline_stats=pipeline_stats,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()

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

        elif action == "sync_from_resume":
            if resume:
                structure = extract_structure(resume.extracted_text, filepath=resume.file_path)
                if structure.get("name") and (not current_user.name or current_user.name == "User"):
                    current_user.name = structure["name"]
                if structure.get("phone"):
                    current_user.phone = structure["phone"]
                if structure.get("location"):
                    current_user.location = structure["location"]
                if structure.get("linkedin_url"):
                    current_user.linkedin_url = structure["linkedin_url"]
                if structure.get("title_role"):
                    current_user.title_role = structure["title_role"]

                pref = JobPreference.query.filter_by(user_id=current_user.id).first()
                if not pref:
                    pref = JobPreference(user_id=current_user.id)
                    db.session.add(pref)
                if structure.get("title_role") and (not pref.target_role or pref.target_role == "Software Engineer"):
                    pref.target_role = structure["title_role"]
                if structure.get("location") and (not pref.location or pref.location == "Remote"):
                    pref.location = structure["location"]

                db.session.commit()
                flash("Personal information successfully auto-filled from your uploaded resume!")
            else:
                flash("No uploaded resume found to sync information from.")

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

    # Auto-sync empty fields from resume on GET if a resume exists
    if resume:
        needs_commit = False
        structure = extract_structure(resume.extracted_text, filepath=resume.file_path)
        if not current_user.phone and structure.get("phone"):
            current_user.phone = structure["phone"]
            needs_commit = True
        if not current_user.location and structure.get("location"):
            current_user.location = structure["location"]
            needs_commit = True
        if not current_user.linkedin_url and structure.get("linkedin_url"):
            current_user.linkedin_url = structure["linkedin_url"]
            needs_commit = True
        if (not current_user.title_role or current_user.title_role == "Job Seeker") and structure.get("title_role"):
            current_user.title_role = structure["title_role"]
            needs_commit = True
        if needs_commit:
            pref = JobPreference.query.filter_by(user_id=current_user.id).first()
            if not pref:
                pref = JobPreference(user_id=current_user.id)
                db.session.add(pref)
            if structure.get("title_role") and (not pref.target_role or pref.target_role == "Software Engineer"):
                pref.target_role = structure["title_role"]
            if structure.get("location") and (not pref.location or pref.location == "Remote"):
                pref.location = structure["location"]
            db.session.commit()

    return render_template("profile.html", resume=resume)
