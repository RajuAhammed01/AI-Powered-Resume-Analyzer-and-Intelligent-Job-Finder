from datetime import datetime, timezone
import json
import logging
import time

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob, utc_now
from app.services.api_client import default_api_client
from app.services.job_api import _CACHE, fetch_jobs, load_seed_jobs
from app.services.job_validator import (
    GLOBAL_JOBS_REGISTRY,
    find_job_by_identifier,
    generate_job_id,
    is_valid_apply_url,
    normalize_apply_url,
)
from app.services.profile_detector import (
    detect_candidate_profile,
    detect_candidate_seniority_intent,
    get_job_ordering_tuple,
)
from app.services.skill_extractor import extract_skills
from app.services.skill_gap import analyze_job_skill_gap

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def get_utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def api_response(data=None, message="Success", meta=None, status_code=200):
    """Standardized API success envelope."""
    envelope = {
        "success": True,
        "message": message,
        "data": data,
        "meta": meta or {},
    }
    envelope["meta"].setdefault("timestamp", get_utc_now_iso())
    return jsonify(envelope), status_code


def api_error(message="An error occurred", code="BAD_REQUEST", details=None, status_code=400):
    """Standardized API error envelope."""
    envelope = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "status_code": status_code,
            "details": details,
        },
        "meta": {
            "timestamp": get_utc_now_iso(),
        },
    }
    return jsonify(envelope), status_code


@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Comprehensive System Health & API Diagnostics.
    Returns:
    - Service status
    - Database connectivity
    - External provider Circuit Breaker metrics
    - In-memory cache & verified seed jobs count
    """
    start_time = time.time()
    db_status = "healthy"
    db_error = None
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    circuit_metrics = default_api_client.get_all_breaker_metrics()
    seed_jobs = load_seed_jobs()

    all_circuits_closed = all(m.get("state") == "CLOSED" for m in circuit_metrics.values())
    overall_status = "healthy" if db_status == "healthy" and all_circuits_closed else "degraded"

    latency_ms = round((time.time() - start_time) * 1000.0, 2)

    return api_response(
        data={
            "status": overall_status,
            "database": {
                "status": db_status,
                "error": db_error,
            },
            "circuits": circuit_metrics,
            "cache": {
                "active_queries_cached": len(_CACHE),
                "verified_seed_jobs_count": len(seed_jobs),
                "global_registry_jobs_count": len(GLOBAL_JOBS_REGISTRY),
            },
        },
        meta={"latency_ms": latency_ms},
    )


@api_bp.route("/circuits", methods=["GET"])
def circuit_status():
    """Returns real-time health and circuit states of all external integrations."""
    return api_response(
        data=default_api_client.get_all_breaker_metrics(),
        message="Circuit breaker metrics retrieved.",
    )


@api_bp.route("/jobs/search", methods=["GET"])
def search_jobs():
    """
    High-Speed Asynchronous Job Search Endpoint.
    Supports filtering by role, location, source, seniority, domain, min_score, and sorting.
    If authenticated, returns personalized AI match analysis and skill coverage.
    """
    start_time = time.time()

    role = request.args.get("q") or request.args.get("role") or ""
    location = request.args.get("location") or "Remote"
    source = request.args.get("source") or "all"
    seniority = request.args.get("seniority", "all").strip().lower()
    domain = request.args.get("domain", "all").strip().lower()
    min_score_arg = request.args.get("min_score", "all").strip().lower()
    sort_query = request.args.get("sort", "score").strip().lower()
    limit = min(int(request.args.get("limit", 25)), 100)

    # Check for authenticated resume context
    user_id = current_user.id if current_user.is_authenticated else None
    resume = None
    candidate_profile = None
    candidate_domain = "software_engineering"
    candidate_title = "Software Engineer"
    resume_skills = []
    resume_text = ""
    is_internship_seeking = False
    is_entry_level_seeking = False

    if user_id:
        resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.upload_date.desc()).first()
        pref = JobPreference.query.filter_by(user_id=user_id).first()
        if resume:
            resume_skills = json.loads(resume.extracted_skills or "[]") if resume.extracted_skills else []
            resume_text = resume.extracted_text or ""
            candidate_profile = detect_candidate_profile(resume_skills, resume_text, current_user.title_role or "")
            candidate_domain = candidate_profile["primary_domain"]
            candidate_title = current_user.title_role if (current_user.title_role and current_user.title_role != "Job Seeker") else candidate_profile["recommended_role"]

            seniority_intent = detect_candidate_seniority_intent(
                resume_text=resume_text,
                declared_title=current_user.title_role or "",
                experience_level_pref=pref.experience_level if pref else "",
                job_type_pref=pref.job_type if pref else "",
                education_text=resume.education or "",
            )
            is_internship_seeking = seniority_intent["is_internship_seeking"]
            is_entry_level_seeking = seniority_intent["is_entry_level_seeking"]

    if not role:
        role = candidate_title if user_id and resume else "Software Engineer"

    # Orchestrated job retrieval with instant fallback
    jobs = fetch_jobs(role=role, location=location, source=source)

    # Score and enrich listings
    enriched_jobs = []
    for job in jobs:
        desc = job.get("job_description", "")
        extracted_job_skills = extract_skills(desc)
        combined_skills = sorted(list(set(extracted_job_skills + (job.get("job_skills") or []))))
        job_copy = dict(job)
        job_copy["job_skills"] = combined_skills

        if user_id and resume:
            analysis = analyze_job_skill_gap(
                resume_skills=resume_skills,
                job_skills=combined_skills,
                resume_text=resume_text,
                job_description=desc,
                candidate_title=candidate_title,
                job_title=job_copy.get("job_title", ""),
                experience_text=resume.experience or "",
                education_text=resume.education or "",
                candidate_domain=candidate_domain,
                is_internship_seeking=is_internship_seeking,
                employment_type=job_copy.get("job_employment_type", ""),
            )
            job_copy["match_score"] = analysis["skill_coverage_score"]
            job_copy["combined_score"] = analysis["final_score"]
            job_copy["is_unrelated_domain"] = analysis["is_unrelated_domain"]
            job_copy["domain_info"] = analysis["domain_info"]
            job_copy["matched_skills"] = analysis["matched_skills"]
            job_copy["missing_skills"] = analysis["missing_skills"]
            job_copy["is_internship"] = analysis.get("is_internship", False)
            job_copy["is_entry_level"] = analysis.get("is_entry_level", False)
            job_copy["display_seniority"] = analysis.get("display_seniority", "Experienced")
        else:
            job_copy["match_score"] = 80
            job_copy["combined_score"] = 80
            job_copy["is_unrelated_domain"] = False
            job_copy["matched_skills"] = []
            job_copy["missing_skills"] = []

        if not job_copy.get("job_id"):
            job_copy["job_id"] = generate_job_id(job_copy)
        GLOBAL_JOBS_REGISTRY[job_copy["job_id"]] = job_copy

        enriched_jobs.append(job_copy)

    # Filtering
    filtered = [j for j in enriched_jobs if not j.get("is_unrelated_domain", False)] if not request.args.get("q") else enriched_jobs

    if seniority in ["internship", "intern"]:
        filtered = [j for j in filtered if j.get("is_internship")]
    elif seniority in ["entry_level", "entry", "junior"]:
        filtered = [j for j in filtered if j.get("is_entry_level")]

    if domain and domain != "all":
        filtered = [j for j in filtered if j.get("domain_info", {}).get("domain") == domain]

    if min_score_arg and min_score_arg.isdigit():
        min_s = int(min_score_arg)
        filtered = [j for j in filtered if j.get("combined_score", 0) >= min_s]

    # Sorting
    if sort_query == "title":
        filtered.sort(key=lambda j: j.get("job_title", "").lower())
    elif sort_query == "company":
        filtered.sort(key=lambda j: (j.get("employer_name") or j.get("company", "")).lower())
    else:
        filtered.sort(
            key=lambda j: get_job_ordering_tuple(
                j,
                is_internship_seeking=is_internship_seeking,
                is_entry_level_seeking=is_entry_level_seeking,
            )
        )

    # Build response payload
    latency_ms = round((time.time() - start_time) * 1000.0, 2)
    return api_response(
        data=filtered[:limit],
        message=f"Found {len(filtered)} matching jobs.",
        meta={
            "count": len(filtered[:limit]),
            "total_matches": len(filtered),
            "latency_ms": latency_ms,
            "query": {
                "role": role,
                "location": location,
                "source": source,
                "seniority": seniority,
                "domain": domain,
            },
        },
    )


@api_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    """
    Retrieve single job listing details by deterministic job_id.
    """
    from app.routes.jobs import USER_JOBS_CACHE

    user_id = current_user.id if current_user.is_authenticated else None
    job = find_job_by_identifier(user_id, job_id, USER_JOBS_CACHE)

    if not job:
        return api_error(
            message=f"Job with identifier '{job_id}' not found.",
            code="JOB_NOT_FOUND",
            status_code=404,
        )

    return api_response(
        data=job,
        message="Job details retrieved successfully.",
    )


@api_bp.route("/jobs/save", methods=["POST"])
@login_required
def save_job_async():
    """
    Asynchronous AJAX Job Bookmark / Save Endpoint.
    Accepts JSON: { "job_id": "...", "notes": "..." } or form data.
    """
    req_data = request.get_json(silent=True) or request.form.to_dict()
    job_id = (req_data.get("job_id") or "").strip()

    if not job_id:
        return api_error("Missing required parameter 'job_id'.", code="MISSING_PARAM", status_code=400)

    from app.routes.jobs import USER_JOBS_CACHE
    job = find_job_by_identifier(current_user.id, job_id, USER_JOBS_CACHE)

    # Fallback to payload metadata if provided
    title = (job.get("job_title") if job else req_data.get("job_title", "Software Developer")).strip()
    company = (job.get("employer_name") or job.get("company") if job else req_data.get("company", "Tech Company")).strip()
    location = (job.get("job_city") or job.get("location") if job else req_data.get("location", "Remote")).strip()
    apply_link = (job.get("job_apply_link") if job else req_data.get("job_apply_link", "")).strip()

    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        count = SavedJob.query.filter_by(user_id=current_user.id).count()
        return api_response(
            data={"job_id": job_id, "saved": True, "saved_jobs_count": count},
            message="Job is already saved.",
        )

    new_saved = SavedJob(
        user_id=current_user.id,
        job_id=job_id,
        job_title=title,
        company=company,
        location=location,
        apply_link=apply_link,
        match_score=job.get("combined_score", 85) if job else 85,
    )
    db.session.add(new_saved)
    db.session.commit()

    count = SavedJob.query.filter_by(user_id=current_user.id).count()
    return api_response(
        data={"job_id": job_id, "saved": True, "saved_jobs_count": count},
        message="Job saved successfully.",
        status_code=201,
    )


@api_bp.route("/jobs/save/<job_id>", methods=["DELETE"])
@login_required
def delete_saved_job_async(job_id: str):
    """
    Asynchronous AJAX Unsave / Remove Bookmark Endpoint.
    """
    saved_item = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if not saved_item:
        # Also check by DB primary key id if an integer was passed
        if job_id.isdigit():
            saved_item = SavedJob.query.filter_by(user_id=current_user.id, id=int(job_id)).first()

    if not saved_item:
        return api_error("Saved job entry not found.", code="JOB_NOT_SAVED", status_code=404)

    db.session.delete(saved_item)
    db.session.commit()

    count = SavedJob.query.filter_by(user_id=current_user.id).count()
    return api_response(
        data={"job_id": job_id, "saved": False, "saved_jobs_count": count},
        message="Job successfully removed from bookmarks.",
    )


@api_bp.route("/jobs/apply-intent", methods=["POST"])
@login_required
def record_apply_intent_async():
    """
    Asynchronous Apply Intent Tracker.
    Records application status in the database and returns verified redirect URL.
    """
    req_data = request.get_json(silent=True) or request.form.to_dict()
    job_id = (req_data.get("job_id") or "").strip()

    from app.routes.jobs import USER_JOBS_CACHE
    job = find_job_by_identifier(current_user.id, job_id, USER_JOBS_CACHE) if job_id else None

    title = (job.get("job_title") if job else req_data.get("job_title", "Software Developer")).strip()
    company = (job.get("employer_name") or job.get("company") if job else req_data.get("company", "Tech Company")).strip()
    raw_apply = (job.get("job_apply_link") if job else req_data.get("job_apply_link", "")).strip()

    norm_apply = normalize_apply_url(raw_apply)
    verified_id = job_id or (job.get("job_id") if job else generate_job_id({"job_title": title, "employer_name": company}))

    # Record in SavedJob table with status='Applied'
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=verified_id).first()
    if existing:
        existing.status = "Applied"
        existing.applied_date = utc_now()
        if norm_apply:
            existing.apply_link = norm_apply
    else:
        applied_record = SavedJob(
            user_id=current_user.id,
            job_id=verified_id,
            job_title=title,
            company=company,
            apply_link=norm_apply,
            location=job.get("job_city") or job.get("location") if job else "Remote",
            match_score=job.get("combined_score", 85) if job else 85,
            status="Applied",
            applied_date=utc_now(),
        )
        db.session.add(applied_record)
    db.session.commit()

    return api_response(
        data={
            "job_id": verified_id,
            "job_title": title,
            "company": company,
            "apply_url": norm_apply,
            "is_valid_url": is_valid_apply_url(norm_apply),
        },
        message="Application intent recorded successfully.",
    )


@api_bp.route("/resume/skills", methods=["GET"])
@login_required
def get_resume_skills_async():
    """
    Returns the authenticated user's extracted skills and candidate domain profile.
    """
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    if not resume:
        return api_error("No resume found for this user.", code="NO_RESUME", status_code=404)

    skills = json.loads(resume.extracted_skills or "[]") if resume.extracted_skills else []
    profile = detect_candidate_profile(skills, resume.extracted_text or "", current_user.title_role or "")

    return api_response(
        data={
            "skills": skills,
            "skills_count": len(skills),
            "profile": profile,
            "upload_date": resume.upload_date.isoformat() if resume.upload_date else None,
        },
        message="Resume skills retrieved successfully.",
    )
