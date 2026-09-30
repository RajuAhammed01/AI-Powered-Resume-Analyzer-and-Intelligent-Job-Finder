import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), default="")
    location = db.Column(db.String(100), default="")
    title_role = db.Column(db.String(100), default="Job Seeker")
    date_of_birth = db.Column(db.String(50), default="")
    linkedin_url = db.Column(db.String(200), default="")
    language = db.Column(db.String(50), default="English")
    theme = db.Column(db.String(20), default="Light")
    notifications_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    resumes = db.relationship("Resume", backref="user", lazy=True, cascade="all, delete-orphan")
    job_preference = db.relationship("JobPreference", backref="user", uselist=False, cascade="all, delete-orphan")
    saved_jobs = db.relationship("SavedJob", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(200), default="Resume.pdf")
    file_path = db.Column(db.String(300))
    extracted_text = db.Column(db.Text)
    extracted_skills = db.Column(db.Text)  # JSON list string
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
    contact_info = db.Column(db.Text)
    completeness_score = db.Column(db.Integer, default=0)
    ats_score = db.Column(db.Integer, default=85)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def skills(self):
        if self.extracted_skills:
            try:
                return json.loads(self.extracted_skills)
            except Exception:
                return [s.strip() for s in self.extracted_skills.split(",") if s.strip()]
        return []


class JobPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    target_role = db.Column(db.String(200), default="Machine Learning Engineer, Data Scientist")
    location_preference = db.Column(db.String(100), default="Any Location")
    location = db.Column(db.String(100), default="Remote")
    experience_level = db.Column(db.String(50), default="Entry Level")
    expected_salary = db.Column(db.String(50), default="Any")
    job_type = db.Column(db.String(50), default="Full-time")
    preferred_skills = db.Column(db.Text, default='["Python", "TensorFlow", "scikit-learn", "SQL"]')

    @property
    def skills_list(self):
        if self.preferred_skills:
            try:
                return json.loads(self.preferred_skills)
            except Exception:
                return [s.strip() for s in self.preferred_skills.split(",") if s.strip()]
        return []


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_id = db.Column(db.String(100), default="j001")
    job_title = db.Column(db.String(200))
    company = db.Column(db.String(200))
    location = db.Column(db.String(100), default="Remote")
    employment_type = db.Column(db.String(50), default="Full-time")
    match_score = db.Column(db.Integer, default=85)
    matched_skills = db.Column(db.Text, default="[]")
    missing_skills = db.Column(db.Text, default="[]")
    apply_link = db.Column(db.String(500))
    saved_date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
