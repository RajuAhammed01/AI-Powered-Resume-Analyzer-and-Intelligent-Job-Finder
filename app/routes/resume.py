import json
import os
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Resume
from app.services.resume_parser import extract_text
from app.services.skill_extractor import extract_skills

resume_bp = Blueprint("resume", __name__)
ALLOWED_EXTENSIONS = {"pdf", "docx"}


def allowed_file(filename):
	return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@resume_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
	if request.method == "POST":
		file = request.files.get("resume")
		if not file or not file.filename:
			flash("No file selected")
			return redirect(request.url)
		if not allowed_file(file.filename):
			flash("Only PDF and DOCX files are allowed")
			return redirect(request.url)

		filename = f"{uuid4().hex}_{secure_filename(file.filename)}"
		filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
		file.save(filepath)
		text = extract_text(filepath)
		resume = Resume(
			user_id=current_user.id,
			file_path=filepath,
			extracted_text=text,
			extracted_skills=json.dumps(extract_skills(text)),
		)
		db.session.add(resume)
		db.session.commit()
		flash("Resume uploaded and text extracted")
		return redirect(url_for("resume.upload"))

	return render_template("upload.html")
