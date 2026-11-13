import time
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import JobPreference, Resume, SavedJob, User
from app.routes.jobs import USER_JOBS_CACHE
from app.services.job_validator import (
    normalize_apply_url,
    is_valid_apply_url,
    generate_job_id,
    GLOBAL_JOBS_REGISTRY,
)
from app.services.job_api import fetch_jobs
from app.services.profile_detector import detect_candidate_profile, detect_candidate_seniority_intent, get_job_ordering_tuple
from app.services.resume_parser import extract_structure
from app.services.skill_extractor import extract_skills
from app.services.skill_gap import analyze_job_skill_gap

main_bp = Blueprint("main", __name__)

USER_DASHBOARD_CACHE = {}


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
    saved_jobs = SavedJob.query.filter_by(user_id=current_user.id).order_by(SavedJob.saved_date.desc()).all()
    extracted_skills_count = len(resume.skills) if resume and resume.skills else 0

    recommended_jobs = []
    top_match_score = None
    skill_gap_summary = []

    candidate_profile = None
    if resume:
        cache_entry = USER_DASHBOARD_CACHE.get(current_user.id)
        if (
            cache_entry
            and cache_entry.get("resume_id") == resume.id
            and (time.time() - cache_entry.get("timestamp", 0) < 1800)
            and cache_entry.get("recommended_jobs")
        ):
            recommended_jobs = cache_entry["recommended_jobs"]
            top_match_score = cache_entry["top_match_score"]
            skill_gap_summary = cache_entry["skill_gap_summary"]
            candidate_profile = cache_entry["candidate_profile"]
        else:
            pref = JobPreference.query.filter_by(user_id=current_user.id).first()
            resume_skills = resume.skills or []
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

            if pref and pref.target_role and pref.target_role not in ["Software Engineer", "Machine Learning Engineer, Data Scientist"]:
                target_role = pref.target_role
            else:
                target_role = candidate_profile["recommended_role"]

            location = (pref.location if pref else None) or "Remote"

            raw_jobs = fetch_jobs(target_role, location)
            processed_jobs = []
            # Process up to 15 prioritized jobs for ultra-fast dashboard generation
            for index, job_item in enumerate(raw_jobs[:15]):
                job = dict(job_item)
                description = job.get("job_description", "")
                extracted_j = extract_skills(description)
                provider_tags = job.get("job_skills") or []
                combined_j = sorted(list(set(extracted_j + provider_tags)))
                job["job_skills"] = combined_j

                # Transparent, multi-signal, domain-aligned skill gap analysis
                analysis = analyze_job_skill_gap(
                    resume_skills=resume_skills,
                    job_skills=combined_j,
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
                processed_jobs.append(job)

            # Filter out unrelated category jobs to ensure top recommended jobs are genuinely suitable
            compatible_jobs = [j for j in processed_jobs if not j.get("is_unrelated_domain", False)]
            display_dashboard_jobs = compatible_jobs if compatible_jobs else processed_jobs
            display_dashboard_jobs.sort(
                key=lambda j: get_job_ordering_tuple(
                    j,
                    is_internship_seeking=is_internship_seeking,
                    is_entry_level_seeking=is_entry_level_seeking,
                )
            )

            # Re-assign cache_id strictly AFTER sorting and ensure all jobs have valid job_ids and registry entries
            for idx, job in enumerate(display_dashboard_jobs):
                job["cache_id"] = idx
                if not job.get("job_id"):
                    job["job_id"] = generate_job_id(job)
                GLOBAL_JOBS_REGISTRY[job["job_id"]] = job

            USER_JOBS_CACHE[current_user.id] = display_dashboard_jobs[:25]
            recommended_jobs = display_dashboard_jobs[:3]

            if recommended_jobs:
                top_match_score = recommended_jobs[0]["combined_score"]

            # Aggregate missing skills from actual live recommended jobs
            missing_skills_map = {}
            sample_jobs = processed_jobs[:10]
            for j in sample_jobs:
                for s in j.get("missing_skills", []):
                    missing_skills_map[s] = missing_skills_map.get(s, 0) + 1

            top_missing_sorted = sorted(missing_skills_map.items(), key=lambda x: x[1], reverse=True)[:5]
            ref_count = max(1, len(sample_jobs))
            for idx, (skill_name, count) in enumerate(top_missing_sorted):
                demand_pct = max(35, min(95, int(round((count / ref_count) * 100))))
                level = "High demand" if demand_pct >= 50 else "Medium demand"
                color = "#ef4444" if demand_pct >= 50 else "#f59e0b"
                skill_gap_summary.append({
                    "skill": skill_name,
                    "demand": demand_pct,
                    "level": level,
                    "color": color,
                    "count": count,
                    "total": ref_count,
                })

            USER_DASHBOARD_CACHE[current_user.id] = {
                "recommended_jobs": recommended_jobs,
                "top_match_score": top_match_score,
                "skill_gap_summary": skill_gap_summary,
                "candidate_profile": candidate_profile,
                "resume_id": resume.id,
                "timestamp": time.time(),
            }

    pipeline_stats = {
        "saved": len([j for j in saved_jobs if (j.status or "Saved").lower() == "saved"]),
        "applied": len([j for j in saved_jobs if (j.status or "").lower() == "applied"]),
        "interview": len([j for j in saved_jobs if (j.status or "").lower() == "interview"]),
        "offer": len([j for j in saved_jobs if (j.status or "").lower() == "offer"]),
        "total": len(saved_jobs),
    }

    return render_template(
        "dashboard.html",
        resume=resume,
        candidate_profile=candidate_profile,
        saved_jobs=saved_jobs,
        extracted_skills_count=extracted_skills_count,
        top_match_score=top_match_score,
        recommended_jobs=recommended_jobs,
        skill_gap_summary=skill_gap_summary,
        pipeline_stats=pipeline_stats,
        is_internship_seeking=is_internship_seeking if 'is_internship_seeking' in locals() else False,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "update_profile":
            current_user.name = request.form.get("name", current_user.name).strip()
            current_user.phone = request.form.get("phone", "").strip()
            current_user.location = request.form.get("location", "").strip()
            current_user.title_role = request.form.get("title_role", current_user.title_role).strip()
            current_user.date_of_birth = request.form.get("date_of_birth", "").strip()
            current_user.linkedin_url = request.form.get("linkedin_url", "").strip()
            db.session.commit()
            flash("Profile information updated successfully.")

        elif action == "sync_from_resume":
            if resume:
                structure = extract_structure(resume.extracted_text, filepath=resume.file_path)
                cand_prof = detect_candidate_profile(resume.skills or [], resume.extracted_text or "", structure.get("title_role", ""))
                role_to_use = structure.get("title_role") or cand_prof["recommended_role"]

                if structure.get("name") and (not current_user.name or current_user.name == "User"):
                    current_user.name = structure["name"]
                if structure.get("phone"):
                    current_user.phone = structure["phone"]
                if structure.get("location"):
                    current_user.location = structure["location"]
                if structure.get("linkedin_url"):
                    current_user.linkedin_url = structure["linkedin_url"]
                if role_to_use:
                    current_user.title_role = role_to_use

                pref = JobPreference.query.filter_by(user_id=current_user.id).first()
                if not pref:
                    pref = JobPreference(user_id=current_user.id)
                    db.session.add(pref)
                if role_to_use:
                    pref.target_role = role_to_use
                if structure.get("location") and (not pref.location or pref.location == "Remote"):
                    pref.location = structure["location"]

                db.session.commit()
                flash("Personal information successfully auto-filled from your uploaded resume!")
            else:
                flash("No uploaded resume found to sync information from.")

        elif action == "change_password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pass):
                flash("Current password is incorrect.")
            elif len(new_pass) < 6:
                flash("New password must be at least 6 characters long.")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                from app.services.auth_dataset import record_login_activity
                record_login_activity(
                    email=current_user.email,
                    status="SUCCESS",
                    user=current_user,
                    failure_reason="Password changed by user",
                )
                flash("Password updated successfully.")

        elif action == "update_settings":
            current_user.language = request.form.get("language", "English")
            current_user.theme = request.form.get("theme", "Light")
            current_user.notifications_enabled = request.form.get("notifications_enabled") == "on"
            db.session.commit()
            flash("Settings updated successfully.")

        return redirect(url_for("main.profile"))

    # Auto-sync empty fields from resume on GET if a resume exists
    if resume:
        needs_commit = False
        structure = extract_structure(resume.extracted_text, filepath=resume.file_path)
        if not current_user.phone and structure.get("phone"):
            current_user.phone = structure["phone"]
            needs_commit = True
        if not current_user.location and structure.get("location"):
            current_user.location = structure["location"]
            needs_commit = True
        if not current_user.linkedin_url and structure.get("linkedin_url"):
            current_user.linkedin_url = structure["linkedin_url"]
            needs_commit = True
        if not current_user.title_role or current_user.title_role in ["Job Seeker", "Software Engineer"]:
            cand_prof = detect_candidate_profile(resume.skills or [], resume.extracted_text or "", structure.get("title_role", ""))
            current_user.title_role = structure.get("title_role") or cand_prof["recommended_role"]
            needs_commit = True
        if needs_commit:
            pref = JobPreference.query.filter_by(user_id=current_user.id).first()
            if not pref:
                pref = JobPreference(user_id=current_user.id)
                db.session.add(pref)
            if current_user.title_role:
                pref.target_role = current_user.title_role
            if structure.get("location") and (not pref.location or pref.location == "Remote"):
                pref.location = structure["location"]
            db.session.commit()

    return render_template("profile.html", resume=resume)
