from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	password_hash = db.Column(db.String(200), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)


class Resume(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	file_path = db.Column(db.String(300))
	extracted_text = db.Column(db.Text)
	extracted_skills = db.Column(db.Text)
	upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class JobPreference(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	target_role = db.Column(db.String(100))
	location = db.Column(db.String(100))
	expected_salary = db.Column(db.String(50))


class SavedJob(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	job_title = db.Column(db.String(200))
	company = db.Column(db.String(200))
	apply_link = db.Column(db.String(500))
	saved_date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
	return db.session.get(User, int(user_id))
