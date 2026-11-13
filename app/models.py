import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def utc_now() -> datetime:
    """Return timezone-naive UTC datetime for clean DB compatibility without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    created_at = db.Column(db.DateTime, default=utc_now)
    last_login = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), default="")
    login_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="active")

    # Relationships
    resumes = db.relationship("Resume", backref="user", lazy=True, cascade="all, delete-orphan")
    job_preference = db.relationship("JobPreference", backref="user", uselist=False, cascade="all, delete-orphan")
    saved_jobs = db.relationship("SavedJob", backref="user", lazy=True, cascade="all, delete-orphan")
    login_history = db.relationship(
        "LoginHistory",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(LoginHistory.timestamp)",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "title_role": self.title_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "signup_date": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_login_date": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None,
            "last_login_ip": self.last_login_ip or "N/A",
            "login_count": self.login_count or 0,
            "status": self.status,
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data

    def to_hashmap_record(self):
        """Full authentication dataset entry with hashed credentials, dates, and login history."""
        return {
            "user_id": self.id,
            "name": self.name,
            "email": self.email,
            "password_hash": self.password_hash,
            "status": self.status,
            "signup_date": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "created_at_iso": self.created_at.isoformat() if self.created_at else None,
            "last_login_date": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None,
            "last_login_iso": self.last_login.isoformat() if self.last_login else None,
            "last_login_ip": self.last_login_ip or "N/A",
            "total_logins": self.login_count or 0,
            "login_history": [item.to_dict() for item in (self.login_history or [])[:10]],
        }


class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # SUCCESS or FAILED
    ip_address = db.Column(db.String(45), default="127.0.0.1")
    user_agent = db.Column(db.String(255), default="")
    failure_reason = db.Column(db.String(200), default="")
    timestamp = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "status": self.status,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "failure_reason": self.failure_reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "formatted_date": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
        }


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
    upload_date = db.Column(db.DateTime, default=utc_now)

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
    status = db.Column(db.String(50), default="Saved")
    applied_date = db.Column(db.DateTime, nullable=True)
    saved_date = db.Column(db.DateTime, default=utc_now)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
