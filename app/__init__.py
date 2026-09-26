import os

from flask import Flask, render_template

from config import Config
from app.extensions import db, login_manager


def create_app():
	app = Flask(__name__)
	app.config.from_object(Config)
	os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

	db.init_app(app)
	login_manager.init_app(app)
	login_manager.login_view = "auth.login"

	from app.routes.main import main_bp
	from app.routes.auth import auth_bp
	from app.routes.resume import resume_bp
	from app.routes.preferences import preferences_bp
	from app.routes.jobs import jobs_bp

	app.register_blueprint(main_bp)
	app.register_blueprint(auth_bp)
	app.register_blueprint(resume_bp)
	app.register_blueprint(preferences_bp)
	app.register_blueprint(jobs_bp)

	@app.errorhandler(404)
	def not_found(error):
		return render_template("errors/404.html"), 404

	@app.errorhandler(413)
	def request_too_large(error):
		return render_template("errors/413.html"), 413

	@app.errorhandler(500)
	def internal_error(error):
		db.session.rollback()
		return render_template("errors/500.html"), 500

	with app.app_context():
		db.create_all()

	return app
