import logging
import os
import traceback

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

from app.extensions import db, login_manager
from config import Config

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except Exception as e:
        app.logger.warning(f"Could not create upload directory: {e}")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    def _is_api_request():
        return (
            request.path.startswith("/api/")
            or request.is_json
            or request.headers.get("Accept") == "application/json"
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )

    @login_manager.unauthorized_handler
    def unauthorized():
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required to access this API resource.",
                    "status_code": 401,
                },
            }), 401
        flash("Please log in to access this page.")
        return redirect(url_for("auth.login", next=request.path))

    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.jobs import jobs_bp
    from app.routes.main import main_bp
    from app.routes.preferences import preferences_bp
    from app.routes.resume import resume_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_bp, url_prefix="/api", name="api_v0")
    # Allow programmatic REST API communication
    csrf.exempt(api_bp)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f"CSRF error: {e.description}")
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {
                    "code": "CSRF_ERROR",
                    "message": e.description,
                    "status_code": 400,
                },
            }), 400
        flash("Session or form validation expired. Please try submitting again.")
        return redirect(request.referrer or url_for("main.index"))

    @app.errorhandler(404)
    def not_found(error):
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested API resource or route was not found.",
                    "status_code": 404,
                },
            }), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_too_large(error):
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Uploaded content exceeds the maximum allowed size limit.",
                    "status_code": 413,
                },
            }), 413
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal 500 Error: {error}\n{traceback.format_exc()}")
        db.session.rollback()
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                    "status_code": 500,
                },
            }), 500
        return render_template("errors/500.html"), 500

    with app.app_context():
        db.create_all()
        if not app.config.get("TESTING"):
            try:
                from app.services.auth_dataset import restore_users_from_auth_dataset
                restore_users_from_auth_dataset()
            except Exception as e:
                app.logger.warning(f"Could not auto-restore users from dataset: {e}")

    return app
