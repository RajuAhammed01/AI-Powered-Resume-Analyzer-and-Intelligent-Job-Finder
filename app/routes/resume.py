import json
import os
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import JobPreference, Resume
from app.services.job_api import fetch_jobs
from app.services.resume_parser import calculate_ats_score, extract_structure, extract_text, validate_upload
from app.services.skill_extractor import extract_skills

resume_bp = Blueprint("resume", __name__)
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@resume_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        try:
            file = request.files.get("resume")
            if not file or not file.filename:
                flash("No file selected. Please choose a PDF or DOCX resume file.")
                return redirect(request.url)

            if not allowed_file(file.filename):
                flash("Only PDF and DOCX files are allowed.")
                return redirect(request.url)

            orig_filename = secure_filename(file.filename)
            filename = f"{uuid4().hex}_{orig_filename}"
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            text = extract_text(filepath)
            structure = extract_structure(text)
            skills = extract_skills(text)
            ats_score = calculate_ats_score(text, structure, skills)

            resume = Resume(
                user_id=current_user.id,
                filename=orig_filename,
                file_path=filepath,
                extracted_text=text or "Extracted resume content.",
                extracted_skills=json.dumps(skills),
                contact_info=structure.get("contact_info", current_user.email),
                education=structure.get("education", "Education not detected."),
                experience=structure.get("experience", "Experience not detected."),
                completeness_score=structure.get("completeness_score", 50),
                ats_score=ats_score,
            )
            db.session.add(resume)
            db.session.commit()

            flash("Resume uploaded and analyzed successfully!")
            return redirect(url_for("resume.resume_analysis", id=resume.id))
        except Exception as e:
            current_app.logger.error(f"Upload processing failed: {e}")
            flash(f"Error processing resume upload: {str(e)}")
            return redirect(url_for("resume.upload"))

    return render_template("upload.html")


@resume_bp.route("/resume/<int:id>")
@login_required
def resume_analysis(id):
    resume = db.session.get(Resume, id)
    if not resume or resume.user_id != current_user.id:
        flash("Resume not found or access denied.")
        return redirect(url_for("main.dashboard"))

    user_skills = set(resume.skills or [])
    pref = JobPreference.query.filter_by(user_id=current_user.id).first()
    target_role = (pref.target_role if pref else None) or "Software Engineer"
    location = (pref.location if pref else None) or "Remote"

    jobs = fetch_jobs(target_role, location)
    missing_freq = {}
    for job in jobs:
        desc = job.get("job_description", "")
        j_skills = extract_skills(desc)
        for s in j_skills:
            if s not in user_skills:
                missing_freq[s] = missing_freq.get(s, 0) + 1

    if not missing_freq:
        general_skills = ["Git", "SQL", "Docker", "Python", "REST APIs", "AWS", "CI/CD", "JavaScript"]
        for s in general_skills:
            if s not in user_skills:
                missing_freq[s] = 1

    sorted_missing = sorted(missing_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    demand_weights = [92, 85, 80, 75, 70]
    skill_gap_recommendations = []
    for idx, (skill_name, _) in enumerate(sorted_missing):
        demand = demand_weights[idx] if idx < len(demand_weights) else 65
        priority = "High" if demand >= 80 else "Medium"
        skill_gap_recommendations.append({
            "skill": skill_name,
            "priority": priority,
            "demand": demand
        })

    return render_template("resume_analysis.html", resume=resume, skill_gap_recommendations=skill_gap_recommendations)
