import re

# 1. Update app/routes/jobs.py
jobs_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\jobs.py"
with open(jobs_path, "r", encoding="utf-8") as f:
    jobs_code = f.read()

# Add imports to jobs.py
if "from app.services.job_validator import" not in jobs_code:
    jobs_code = jobs_code.replace(
        "from app.services.skill_gap import analyze_job_skill_gap, suggest_learning",
        "from app.services.skill_gap import analyze_job_skill_gap, suggest_learning\nfrom app.services.job_validator import (\n    normalize_apply_url,\n    is_valid_apply_url,\n    generate_job_id,\n    GLOBAL_JOBS_REGISTRY,\n    find_job_by_identifier,\n)"
    )

# Replace results() post-processing in jobs.py
old_results_cache = """        job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})
        job["cache_id"] = index

    # Filter out unrelated roles unless user explicitly queried for something specific
    compatible_jobs = [j for j in jobs if not j.get("is_unrelated_domain", False)]
    display_jobs = jobs if search_query else (compatible_jobs if compatible_jobs else jobs)

    # Order jobs with priority: relevant internships first for internship seekers, then entry-level, then experienced
    display_jobs.sort(
        key=lambda j: get_job_ordering_tuple(
            j,
            is_internship_seeking=is_internship_seeking,
            is_entry_level_seeking=is_entry_level_seeking,
        )
    )
    USER_JOBS_CACHE[current_user.id] = display_jobs[:30]"""

new_results_cache = """        job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})

    # Filter out unrelated roles unless user explicitly queried for something specific
    compatible_jobs = [j for j in jobs if not j.get("is_unrelated_domain", False)]
    display_jobs = jobs if search_query else (compatible_jobs if compatible_jobs else jobs)

    # Order jobs with priority: relevant internships first for internship seekers, then entry-level, then experienced
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

    USER_JOBS_CACHE[current_user.id] = display_jobs[:30]"""

assert old_results_cache in jobs_code, "old_results_cache not found in jobs.py"
jobs_code = jobs_code.replace(old_results_cache, new_results_cache)

# Replace job_detail, apply_redirect, and apply_job routes in jobs.py
old_routes_section = """@jobs_bp.route("/job/<int:index>")
@login_required
def job_detail(index):
    jobs = USER_JOBS_CACHE.get(current_user.id, [])
    if 0 <= index < len(jobs):
        job = jobs[index]
        resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).first()
        learning_resources = suggest_learning(job.get("missing_skills", []))
        similar_jobs = [j for i, j in enumerate(jobs) if i != index][:3]
        return render_template(
            "job_detail.html",
            job=job,
            index=index,
            resume=resume,
            learning_resources=learning_resources,
            similar_jobs=similar_jobs,
        )

    flash("Job details not found in cache. Refreshing recommendations.")
    return redirect(url_for("jobs.results"))


@jobs_bp.route("/job/apply/<int:index>")
@login_required
def apply_redirect(index):
    \"\"\"
    Direct 'Apply Now' Redirector.
    Records the application in SavedJob and immediately redirects the user
    directly to the authentic original job application page.
    \"\"\"
    jobs = USER_JOBS_CACHE.get(current_user.id, [])
    if 0 <= index < len(jobs):
        job = jobs[index]
        apply_url = job.get("job_apply_link", "").strip()
        job_title = job.get("job_title", "").strip()
        company = (job.get("employer_name") or job.get("company", "")).strip()
        location = (job.get("job_city") or job.get("location", "Remote")).strip()
        match_score = int(job.get("combined_score", 85))

        # Auto-track under Applied status in pipeline
        if job_title and company:
            existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
            if existing:
                existing.status = "Applied"
                if not existing.applied_date:
                    existing.applied_date = datetime.utcnow()
                if apply_url:
                    existing.apply_link = apply_url
            else:
                applied = SavedJob(
                    user_id=current_user.id,
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

        if apply_url and apply_url != "#":
            return redirect(apply_url)

    flash("Original application link is unavailable.")
    return redirect(url_for("jobs.results"))


@jobs_bp.route("/apply-job", methods=["POST"])
@login_required
def apply_job():
    \"\"\"
    Form submission for Quick Apply with Resume.
    Saves the application record and redirects directly to the original job application portal.
    \"\"\"
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    match_score = int(request.form.get("match_score", 85))

    existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
    if existing:
        existing.status = "Applied"
        existing.applied_date = datetime.utcnow()
        if apply_link:
            existing.apply_link = apply_link
    else:
        applied = SavedJob(
            user_id=current_user.id,
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
    flash(f"🎉 Application recorded for {job_title} at {company}! Redirecting to the official application portal...")
    if apply_link and apply_link != "#":
        return redirect(apply_link)
    return redirect(request.referrer or url_for("jobs.saved_jobs"))"""

new_routes_section = """@jobs_bp.route("/job/<index>")
@login_required
def job_detail(index):
    \"\"\"
    Job details view with accurate job resolution by stable job_id or verified index.
    \"\"\"
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
    \"\"\"
    Direct 'Apply Now' Redirector with Strict Job ID & Application URL Validation.
    Guarantees that users are redirected ONLY to the verified application URL for the selected job.
    Never redirects users to another job or unrelated listing.
    \"\"\"
    job = find_job_by_identifier(current_user.id, index, USER_JOBS_CACHE)
    if not job:
        flash("The selected job opening could not be found or your session has expired. Please refresh your recommendations.")
        return redirect(url_for("jobs.results"))

    raw_apply_url = job.get("job_apply_link", "").strip()
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
    \"\"\"
    Form submission for Quick Apply with Resume.
    Validates job metadata and application URL before recording and redirecting.
    \"\"\"
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
        return redirect(request.referrer or url_for("jobs.saved_jobs"))"""

assert old_routes_section in jobs_code, "old_routes_section not found in jobs.py"
jobs_code = jobs_code.replace(old_routes_section, new_routes_section)

# Also update save_job in jobs.py
old_save_job = """@jobs_bp.route("/save-job", methods=["POST"])
@login_required
def save_job():
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    apply_link = request.form.get("apply_link", "").strip()
    location = request.form.get("location", "Remote").strip()
    match_score = int(request.form.get("match_score", 85))

    # Avoid duplicate saves
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_title=job_title, company=company).first()
    if not existing:
        saved = SavedJob(
            user_id=current_user.id,
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
        flash("Job is already saved.")

    return redirect(request.referrer or url_for("jobs.saved_jobs"))"""

new_save_job = """@jobs_bp.route("/save-job", methods=["POST"])
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

    return redirect(request.referrer or url_for("jobs.saved_jobs"))"""

assert old_save_job in jobs_code, "old_save_job not found in jobs.py"
jobs_code = jobs_code.replace(old_save_job, new_save_job)

with open(jobs_path, "w", encoding="utf-8") as f:
    f.write(jobs_code)
print("Updated app/routes/jobs.py successfully.")


# 2. Update app/routes/main.py
main_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_code = f.read()

if "from app.services.job_validator import" not in main_code:
    main_code = main_code.replace(
        "from app.routes.jobs import USER_JOBS_CACHE",
        "from app.routes.jobs import USER_JOBS_CACHE\nfrom app.services.job_validator import (\n    normalize_apply_url,\n    is_valid_apply_url,\n    generate_job_id,\n    GLOBAL_JOBS_REGISTRY,\n)"
    )

old_main_cache = """            job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})
            job["cache_id"] = index
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
        USER_JOBS_CACHE[current_user.id] = display_dashboard_jobs[:25]
        recommended_jobs = display_dashboard_jobs[:3]"""

new_main_cache = """            job["detailed_diagnostic"] = analysis.get("detailed_diagnostic", {})
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
        recommended_jobs = display_dashboard_jobs[:3]"""

assert old_main_cache in main_code, "old_main_cache not found in main.py"
main_code = main_code.replace(old_main_cache, new_main_cache)

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_code)
print("Updated app/routes/main.py successfully.")

