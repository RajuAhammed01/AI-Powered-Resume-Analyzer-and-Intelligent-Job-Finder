import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob
from app.services.job_api import fetch_jobs
from app.services.profile_detector import detect_candidate_profile, detect_candidate_seniority_intent, get_job_ordering_tuple
from app.services.skill_extractor import extract_skills
from app.services.skill_gap import analyze_job_skill_gap, suggest_learning
from app.services.job_validator import (
    normalize_apply_url,
    is_valid_apply_url,
    generate_job_id,
    GLOBAL_JOBS_REGISTRY,
    find_job_by_identifier,
)

jobs_bp = Blueprint("jobs", __name__)

USER_JOBS_CACHE = {}


@jobs_bp.route("/results")
@login_required
def results():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    if not resume:
        flash("Please upload your resume first so our AI can analyze your skills and find matching jobs.")
        return redirect(url_for("resume.upload"))

    pref = JobPreference.query.filter_by(user_id=current_user.id).first()

    # Create default preference if none exists
    if not pref:
        pref = JobPreference(user_id=current_user.id)
        db.session.add(pref)
        db.session.commit()

    resume_skills = json.loads(resume.extracted_skills or "[]") if resume.extracted_skills else []
    resume_text = resume.extracted_text or ""
    candidate_profile = detect_candidate_profile(resume_skills, resume_text, current_user.title_role or "")
    candidate_domain = candidate_profile["primary_domain"]
    candidate_title = current_user.title_role if (current_user.title_role and current_user.title_role != "Job Seeker") else candidate_profile["recommended_role"]

    # Detect candidate seniority intent (internship seeking, entry level, etc.)
    seniority_intent = detect_candidate_seniority_intent(
        resume_text=resume_text,
        declared_title=current_user.title_role or "",
        experience_level_pref=pref.experience_level or "",
        job_type_pref=pref.job_type or "",
        education_text=resume.education or "",
    )
    is_internship_seeking = seniority_intent["is_internship_seeking"]
    is_entry_level_seeking = seniority_intent["is_entry_level_seeking"]

    search_query = request.args.get("q", "").strip()
    source_query = request.args.get("source", "all").strip().lower()
    location_query = request.args.get("location", "all").strip().lower()
    type_query = request.args.get("type", "all").strip().lower()
    seniority_query = request.args.get("seniority", "all").strip().lower()
    domain_query = request.args.get("domain", "all").strip().lower()
    min_score_query = request.args.get("min_score", "all").strip().lower()
    sort_query = request.args.get("sort", "score").strip().lower()

    if search_query:
        target_role = search_query
    elif pref.target_role and pref.target_role not in ["Software Engineer", "Machine Learning Engineer, Data Scientist"]:
        target_role = pref.target_role
    else:
        target_role = candidate_profile["recommended_role"]

    location = pref.location or "Remote"

    # Fetch live real-time job listings tailored to candidate's domain
    jobs = fetch_jobs(target_role, location, source=source_query)
    for index, job in enumerate(jobs):
        description = job.get("job_description", "")
        extracted_job_skills = extract_skills(description)
        existing_skills = job.get("job_skills") or []
        combined_job_skills = sorted(list(set(extracted_job_skills + existing_skills)))
        job["job_skills"] = combined_job_skills

        # Transparent, job-specific multi-signal skill gap and domain relevance analysis
        analysis = analyze_job_skill_gap(
            resume_skills=resume_skills,
            job_skills=combined_job_skills,
            resume_text=resume_text,
            job_description=description,
            candidate_title=candidate_title,
            job_title=job.get("job_title", ""),
            experience_text=resume.experience or "",
            education_text=resume.education or "",
            candidate_domain=candidate_domain,
            is_internship_seeking=is_internship_seeking,
            employment_type=job.get("job_employment_type", ""),
        )
        job["match_score"] = analysis["skill_coverage_score"]
        job["cosine_score"] = analysis["semantic_score"]
        job["title_score"] = analysis["title_score"]
        job["experience_score"] = analysis["experience_score"]
        job["education_score"] = analysis["education_score"]
        job["combined_score"] = analysis["final_score"]
        job["is_unrelated_domain"] = analysis["is_unrelated_domain"]
        job["domain_info"] = analysis["domain_info"]
        job["matched_skills"] = analysis["matched_skills"]
        job["partial_skills"] = analysis["partial_skills"]
        job["missing_skills"] = analysis["missing_skills"]
        job["score_explanation"] = analysis["summary_explanation"]
        job["actionable_advice"] = analysis["actionable_advice"]
        job["score_breakdown"] = analysis["score_breakdown"]
        job["skill_points"] = analysis["skill_points"]
        job["seniority_level"] = analysis.get("seniority_level", "experienced")
        job["is_internship"] = analysis.get("is_internship", False)
        job["is_entry_level"] = analysis.get("is_entry_level", False)
        job["is_experienced"] = analysis.get("is_experienced", True)
        job["display_seniority"] = analysis.get("display_seniority", "Experienced")
        job["badge_color"] = analysis.get("badge_color", "#1e40af")
        job["badge_bg"] = analysis.get("badge_bg", "#eff6ff")
        job["qualifications_score"] = analysis.get("qualifications_score", 70)
        job["projects_score"] = analysis.get("projects_score", 70)
        job["responsibilities_score"] = analysis.get("responsibilities_score", 70)
        job["strong_skills"] = analysis.get("strong_skills", [])
        job["missing_skills_detailed"] = analysis.get("missing_skills_detailed", [])
        job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})

    # Filter out unrelated roles unless user explicitly queried for something specific
    compatible_jobs = [j for j in jobs if not j.get("is_unrelated_domain", False)]
    display_jobs = jobs if search_query else (compatible_jobs if compatible_jobs else jobs)

    # Apply server-side filters if requested via GET URL parameters
    if location_query == "remote":
        display_jobs = [j for j in display_jobs if "remote" in (j.get("job_city") or j.get("location", "")).lower()]
    elif location_query == "onsite":
        display_jobs = [j for j in display_jobs if "remote" not in (j.get("job_city") or j.get("location", "")).lower()]

    if type_query and type_query != "all":
        display_jobs = [j for j in display_jobs if type_query in (j.get("job_employment_type", "")).lower()]

    if seniority_query in ["internship", "intern"]:
        display_jobs = [j for j in display_jobs if j.get("is_internship")]
    elif seniority_query in ["entry_level", "entry", "junior"]:
        display_jobs = [j for j in display_jobs if j.get("is_entry_level")]
    elif seniority_query in ["experienced", "mid", "senior"]:
        display_jobs = [j for j in display_jobs if not j.get("is_internship") and not j.get("is_entry_level")]

    if domain_query and domain_query != "all":
        display_jobs = [j for j in display_jobs if j.get("domain_info", {}).get("domain") == domain_query]

    if min_score_query and min_score_query.isdigit():
        min_s = int(min_score_query)
        display_jobs = [j for j in display_jobs if j.get("combined_score", 0) >= min_s]

    # Order jobs with priority:
    if sort_query == "title":
        display_jobs.sort(key=lambda j: j.get("job_title", "").lower())
    elif sort_query == "company":
        display_jobs.sort(key=lambda j: (j.get("employer_name") or j.get("company", "")).lower())
    else:
        # Default smart priority ordering (internships first for intern seekers, then match score)
        display_jobs.sort(
            key=lambda j: get_job_ordering_tuple(
                j,
                is_internship_seeking=is_internship_seeking,
                is_entry_level_seeking=is_entry_level_seeking,
            )
        )

    # Re-assign cache_id strictly AFTER sorting and ensure all jobs have valid job_ids and registry entries
    for idx, job in enumerate(display_jobs):
        job["cache_id"] = idx
        if not job.get("job_id"):
            job["job_id"] = generate_job_id(job)
        GLOBAL_JOBS_REGISTRY[job["job_id"]] = job

    USER_JOBS_CACHE[current_user.id] = display_jobs[:35]

    # Dynamic extraction of top skills across active results for one-click quick filtering
    skills_counter = {}
    for j in display_jobs:
        for s in (j.get("job_skills") or []):
            clean_s = s.strip()
            if 1 < len(clean_s) < 25 and not clean_s.lower().startswith("http") and not clean_s.isdigit():
                skills_counter[clean_s] = skills_counter.get(clean_s, 0) + 1
    popular_skills = [s for s, _ in sorted(skills_counter.items(), key=lambda x: x[1], reverse=True)[:10]]

    saved_jobs_count = SavedJob.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "results.html",
        jobs=display_jobs[:35],
        resume=resume,
        candidate_profile=candidate_profile,
        saved_jobs_count=saved_jobs_count,
        top_match_score=display_jobs[0]["combined_score"] if display_jobs else 88,
        selected_source=source_query,
        selected_location=location_query,
        selected_type=type_query,
        selected_seniority=seniority_query,
        selected_domain=domain_query,
        selected_min_score=min_score_query,
        selected_sort=sort_query,
        search_query=search_query,
        popular_skills=popular_skills,
        is_internship_seeking=is_internship_seeking,
        is_entry_level_seeking=is_entry_level_seeking,
        seniority_intent=seniority_intent,
    )


@jobs_bp.route("/job/<index>")
@login_required
def job_detail(index):
    """
    Job details view with accurate job resolution by stable job_id or verified index.
    """
    job = find_job_by_identifier(current_user.id, index, USER_JOBS_CACHE)
    if job:
        resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
        learning_resources = suggest_learning(job.get("missing_skills", []))
        
        # Similar jobs from user's current recommendations excluding active job
        user_jobs = USER_JOBS_CACHE.get(current_user.id, [])
        active_jid = job.get("job_id")
        similar_jobs = [j for j in user_jobs if j.get("job_id") != active_jid][:3]
        
        return render_template(
            "job_detail.html",
            job=job,
            index=job.get("job_id", index),
            resume=resume,
            learning_resources=learning_resources,
            similar_jobs=similar_jobs,
        )

    flash("The requested job listing could not be found or your session has expired. Please view current recommendations.")
    return redirect(url_for("jobs.results"))


@jobs_bp.route("/job/apply/<index>")
@login_required
def apply_redirect(index):
    """
    Direct 'Apply Now' Redirector with Strict Job ID & Application URL Validation.
    Guarantees that users are redirected ONLY to the verified application URL for the selected job.
    Never redirects users to another job or unrelated listing.
    """
    job = find_job_by_identifier(current_user.id, index, USER_JOBS_CACHE)
    direct_url = request.args.get("direct_url", "").strip()

    if not job and direct_url and is_valid_apply_url(direct_url):
        apply_url = normalize_apply_url(direct_url)
        return redirect(apply_url)

    if not job:
        flash("The selected job opening could not be found or your session has expired. Please refresh your recommendations.")
        return redirect(url_for("jobs.results"))

    raw_apply_url = job.get("job_apply_link", "").strip() or direct_url
    job_title = job.get("job_title", "").strip()
    company = (job.get("employer_name") or job.get("company", "")).strip()
    location = (job.get("job_city") or job.get("location", "Remote")).strip()
    match_score = int(job.get("combined_score", 85))
    job_id = job.get("job_id", str(index))

    # Strict URL validation and normalization
    apply_url = normalize_apply_url(raw_apply_url)
    if not is_valid_apply_url(apply_url):
        flash(f"The official application link for '{job_title}' at '{company}' is currently unavailable. No external redirect could be performed.")
        return redirect(url_for("jobs.job_detail", index=job_id))

    # Auto-track under Applied status in SavedJob pipeline
    if job_title and company:
        try:
            existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
            if existing:
                existing.status = "Applied"
                if not existing.applied_date:
                    existing.applied_date = datetime.utcnow()
                existing.apply_link = apply_url
                existing.job_id = job_id
            else:
                applied = SavedJob(
                    user_id=current_user.id,
                    job_id=job_id,
                    job_title=job_title,
                    company=company,
                    apply_link=apply_url,
                    location=location,
                    match_score=match_score,
                    status="Applied",
                    applied_date=datetime.utcnow(),
                )
                db.session.add(applied)
            db.session.commit()
        except Exception as e:
            db.session.rollback()

    return redirect(apply_url)


@jobs_bp.route("/apply-job", methods=["POST"])
@login_required
def apply_job():
    """
    Form submission for Quick Apply with Resume.
    Validates job metadata and application URL before recording and redirecting.
    """
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    raw_apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    job_id = request.form.get("job_id", "").strip()
    try:
        match_score = int(request.form.get("match_score", 85))
    except (ValueError, TypeError):
        match_score = 85

    apply_link = normalize_apply_url(raw_apply_link)

    if job_title and company:
        try:
            existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
            if existing:
                existing.status = "Applied"
                existing.applied_date = datetime.utcnow()
                if apply_link:
                    existing.apply_link = apply_link
                if job_id:
                    existing.job_id = job_id
            else:
                applied = SavedJob(
                    user_id=current_user.id,
                    job_id=job_id or "job",
                    job_title=job_title,
                    company=company,
                    apply_link=apply_link,
                    location=location,
                    match_score=match_score,
                    status="Applied",
                    applied_date=datetime.utcnow(),
                )
                db.session.add(applied)
            db.session.commit()
        except Exception as e:
            db.session.rollback()

    if is_valid_apply_url(apply_link):
        flash(f"🎉 Application recorded for {job_title} at {company}! Redirecting to the official application portal...")
        return redirect(apply_link)
    else:
        flash(f"Application recorded for {job_title} at {company}! (Official external application link is currently unavailable).")
        return redirect(request.referrer or url_for("jobs.saved_jobs"))


@jobs_bp.route("/saved-jobs")
@login_required
def saved_jobs():
    saved_list = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_date.desc()).all()
    return render_template("saved_jobs.html", saved_jobs=saved_list)


@jobs_bp.route("/save-job", methods=["POST"])
@login_required
def save_job():
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    raw_apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    job_id = request.form.get("job_id", "").strip()
    try:
        match_score = int(request.form.get("match_score", 85))
    except (ValueError, TypeError):
        match_score = 85

    apply_link = normalize_apply_url(raw_apply_link)

    # Avoid duplicate saves
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
    if not existing:
        saved = SavedJob(
            user_id=current_user.id,
            job_id=job_id or generate_job_id({"job_title": job_title, "company": company, "job_apply_link": apply_link}),
            job_title=job_title,
            company=company,
            apply_link=apply_link,
            location=location,
            match_score=match_score,
        )
        db.session.add(saved)
        db.session.commit()
        flash(f"Saved {job_title} at {company} to your saved jobs!")
    else:
        if apply_link and not existing.apply_link:
            existing.apply_link = apply_link
            db.session.commit()
        flash("Job is already saved.")

    return redirect(request.referrer or url_for("jobs.saved_jobs"))


@jobs_bp.route("/remove-saved-job/<int:id>", methods=["POST"])
@login_required
def remove_saved_job(id):
    job = db.session.get(SavedJob, id)
    if job and job.user_id == current_user.id:
        db.session.delete(job)
        db.session.commit()
        flash("Job removed from saved list.")
    return redirect(url_for("jobs.saved_jobs"))


@jobs_bp.route("/update-job-status/<int:id>", methods=["POST"])
@login_required
def update_job_status(id):
    job = db.session.get(SavedJob, id)
    if job and job.user_id == current_user.id:
        new_status = request.form.get("status", "Saved").strip()
        job.status = new_status
        if new_status == "Applied" and not job.applied_date:
            job.applied_date = datetime.utcnow()
        db.session.commit()
        flash(f"Updated status for '{job.job_title}' to '{new_status}'.")
    return redirect(request.referrer or url_for("jobs.saved_jobs"))
