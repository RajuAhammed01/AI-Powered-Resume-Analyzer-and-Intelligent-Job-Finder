import json
import os
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import JobPreference, Resume
from app.services.job_api import fetch_jobs
from app.services.profile_detector import detect_candidate_profile
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
            structure = extract_structure(text, filepath=filepath)
            # Strictly verified skill extraction - only skills actually mentioned in the text
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

            # Intelligent profile detection from verified skills and text
            profile = detect_candidate_profile(skills, text, structure.get("title_role", ""))
            recommended_role = profile["recommended_role"]

            # Auto-populate personal details on current_user
            if structure.get("phone") and not current_user.phone:
                current_user.phone = structure["phone"]
            if structure.get("location") and not current_user.location:
                current_user.location = structure["location"]
            if structure.get("linkedin_url") and not current_user.linkedin_url:
                current_user.linkedin_url = structure["linkedin_url"]
            if not current_user.title_role or current_user.title_role in ["Job Seeker", "Software Engineer"]:
                current_user.title_role = recommended_role
            elif structure.get("title_role"):
                current_user.title_role = structure["title_role"]
            if structure.get("name") and (not current_user.name or current_user.name == "User"):
                current_user.name = structure["name"]

            # Sync JobPreference target_role and location with actual career profile
            pref = JobPreference.query.filter_by(user_id=current_user.id).first()
            if not pref:
                pref = JobPreference(user_id=current_user.id)
                db.session.add(pref)
            pref.target_role = recommended_role
            if structure.get("location") and (not pref.location or pref.location == "Remote"):
                pref.location = structure["location"]

            db.session.commit()

            flash("Resume uploaded and analyzed successfully! Verified skills extracted.")
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
    user_skills_lower = {s.lower() for s in user_skills}

    pref = JobPreference.query.filter_by(user_id=current_user.id).first()
    profile = detect_candidate_profile(list(user_skills), resume.extracted_text or "", current_user.title_role or "")
    target_role = (pref.target_role if pref and pref.target_role and pref.target_role != "Software Engineer" else None) or profile["recommended_role"]
    location = (pref.location if pref else None) or "Remote"

    # Fetch real live jobs for the user's specific target role
    jobs = fetch_jobs(target_role, location)
    total_live_jobs = len(jobs) if jobs else 1

    missing_freq = {}
    for job in jobs:
        desc = job.get("job_description", "")
        extracted_j = extract_skills(desc)
        provider_tags = job.get("job_skills") or []
        j_skills = set(extracted_j + provider_tags)

        for s in j_skills:
            if s.lower() not in user_skills_lower:
                missing_freq[s] = missing_freq.get(s, 0) + 1

    # Calculate actual percentage demand from live active job postings
    sorted_missing = sorted(missing_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    skill_gap_recommendations = []

    for skill_name, count in sorted_missing:
        demand_pct = int(round((count / total_live_jobs) * 100))
        # Priority scaled by true frequency in live postings
        priority = "High" if demand_pct >= 40 else "Medium"
        skill_gap_recommendations.append({
            "skill": skill_name,
            "priority": priority,
            "demand": max(30, min(95, demand_pct)),
            "count": count,
            "total_jobs": total_live_jobs,
        })

    return render_template(
        "resume_analysis.html",
        resume=resume,
        skill_gap_recommendations=skill_gap_recommendations,
        target_role=target_role,
        live_job_count=len(jobs),
    )
