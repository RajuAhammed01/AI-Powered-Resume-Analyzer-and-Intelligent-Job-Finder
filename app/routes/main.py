from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
	return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
	return render_template("dashboard.html")
