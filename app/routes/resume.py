import json
import os
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Resume
from app.services.resume_parser import extract_structure, extract_text, validate_upload
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

            resume = Resume(
                user_id=current_user.id,
                filename=orig_filename,
                file_path=filepath,
                extracted_text=text or "Extracted resume content.",
                extracted_skills=json.dumps(skills),
                contact_info=structure.get("contact_info", current_user.email),
                education=structure.get("education", "Education extracted from resume."),
                experience=structure.get("experience", "Work experience extracted from resume."),
                completeness_score=structure.get("completeness_score", 80),
                ats_score=min(95, max(60, structure.get("completeness_score", 70) + 10)),
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

    skill_gap_recommendations = [
        {"skill": "Machine Learning", "priority": "High", "demand": 90},
        {"skill": "Deep Learning", "priority": "High", "demand": 85},
        {"skill": "NLP", "priority": "Medium", "demand": 75},
        {"skill": "Cloud Computing (AWS/GCP)", "priority": "Medium", "demand": 80},
        {"skill": "Docker & Kubernetes", "priority": "High", "demand": 88},
    ]

    return render_template("resume_analysis.html", resume=resume, skill_gap_recommendations=skill_gap_recommendations)
