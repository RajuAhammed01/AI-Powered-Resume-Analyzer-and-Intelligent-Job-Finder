from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
	if request.method == "POST":
		name = request.form.get("name", "").strip()
		email = request.form.get("email", "").strip().lower()
		password = request.form.get("password", "")

		if not name or not email or not password:
			flash("All fields are required")
			return redirect(url_for("auth.register"))

		if User.query.filter_by(email=email).first():
			flash("Email already exists")
			return redirect(url_for("auth.register"))

		user = User(name=name, email=email)
		user.set_password(password)
		db.session.add(user)
		db.session.commit()
		flash("Registered successfully. Please login.")
		return redirect(url_for("auth.login"))

	return render_template("auth/register.html", is_auth_page=True)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		email = request.form.get("email", "").strip().lower()
		password = request.form.get("password", "")
		user = User.query.filter_by(email=email).first()

		if user and user.check_password(password):
			login_user(user)
			return redirect(url_for("main.dashboard"))

		flash("Invalid email or password")

	return render_template("auth/login.html", is_auth_page=True)


@auth_bp.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("main.index"))
