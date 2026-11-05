import os

# 1. Update app/routes/jobs.py
jobs_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\jobs.py"
with open(jobs_path, "r", encoding="utf-8") as f:
    jobs_code = f.read()

# Update import
jobs_code = jobs_code.replace(
    "from app.services.profile_detector import detect_candidate_profile",
    "from app.services.profile_detector import detect_candidate_profile, detect_candidate_seniority_intent, get_job_ordering_tuple"
)

# Update seniority intent and analyze_job_skill_gap call
old_jobs_target = """    candidate_domain = candidate_profile["primary_domain"]
    candidate_title = current_user.title_role if (current_user.title_role and current_user.title_role != "Job Seeker") else candidate_profile["recommended_role"]

    search_query = request.args.get("q", "").strip()"""

new_jobs_target = """    candidate_domain = candidate_profile["primary_domain"]
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

    search_query = request.args.get("q", "").strip()"""

if old_jobs_target in jobs_code:
    jobs_code = jobs_code.replace(old_jobs_target, new_jobs_target)
else:
    print("Warning: old_jobs_target not matched in jobs.py")

# Update analyze_job_skill_gap call in jobs.py
old_analysis_call = """        # Transparent, job-specific multi-signal skill gap and domain relevance analysis
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
        job["cache_id"] = index"""

new_analysis_call = """        # Transparent, job-specific multi-signal skill gap and domain relevance analysis
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
        job["cache_id"] = index"""

if old_analysis_call in jobs_code:
    jobs_code = jobs_code.replace(old_analysis_call, new_analysis_call)
else:
    print("Warning: old_analysis_call not matched in jobs.py")

# Update sorting and render_template in jobs.py
old_sort_jobs = """    # Sort strictly prioritizing compatible domain roles first, then score descending
    display_jobs.sort(key=lambda j: (not j.get("is_unrelated_domain", False), j.get("combined_score", 0)), reverse=True)
    USER_JOBS_CACHE[current_user.id] = display_jobs[:30]

    saved_jobs_count = SavedJob.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "results.html",
        jobs=display_jobs[:30],
        resume=resume,
        candidate_profile=candidate_profile,
        saved_jobs_count=saved_jobs_count,
        top_match_score=display_jobs[0]["combined_score"] if display_jobs else 88,
        selected_source=source_query,
    )"""

new_sort_jobs = """    # Order jobs with priority: relevant internships first for internship seekers, then entry-level, then experienced
    display_jobs.sort(
        key=lambda j: get_job_ordering_tuple(
            j,
            is_internship_seeking=is_internship_seeking,
            is_entry_level_seeking=is_entry_level_seeking,
        )
    )
    USER_JOBS_CACHE[current_user.id] = display_jobs[:30]

    saved_jobs_count = SavedJob.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "results.html",
        jobs=display_jobs[:30],
        resume=resume,
        candidate_profile=candidate_profile,
        saved_jobs_count=saved_jobs_count,
        top_match_score=display_jobs[0]["combined_score"] if display_jobs else 88,
        selected_source=source_query,
        is_internship_seeking=is_internship_seeking,
        is_entry_level_seeking=is_entry_level_seeking,
        seniority_intent=seniority_intent,
    )"""

if old_sort_jobs in jobs_code:
    jobs_code = jobs_code.replace(old_sort_jobs, new_sort_jobs)
else:
    print("Warning: old_sort_jobs not matched in jobs.py")

with open(jobs_path, "w", encoding="utf-8") as f:
    f.write(jobs_code)
print("jobs.py updated successfully.")


# 2. Update app/routes/main.py
main_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\routes\main.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_code = f.read()

main_code = main_code.replace(
    "from app.services.profile_detector import detect_candidate_profile",
    "from app.services.profile_detector import detect_candidate_profile, detect_candidate_seniority_intent, get_job_ordering_tuple"
)

old_main_target = """        candidate_profile = detect_candidate_profile(resume_skills, resume_text, current_user.title_role or "")
        candidate_domain = candidate_profile["primary_domain"]
        candidate_title = current_user.title_role if (current_user.title_role and current_user.title_role != "Job Seeker") else candidate_profile["recommended_role"]"""

new_main_target = """        candidate_profile = detect_candidate_profile(resume_skills, resume_text, current_user.title_role or "")
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
        is_entry_level_seeking = seniority_intent["is_entry_level_seeking"]"""

if old_main_target in main_code:
    main_code = main_code.replace(old_main_target, new_main_target)
else:
    print("Warning: old_main_target not matched in main.py")

old_main_analysis = """            # Transparent, multi-signal, domain-aligned skill gap analysis
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
            job["cache_id"] = index
            processed_jobs.append(job)"""

new_main_analysis = """            # Transparent, multi-signal, domain-aligned skill gap analysis
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
            job["cache_id"] = index
            processed_jobs.append(job)"""

if old_main_analysis in main_code:
    main_code = main_code.replace(old_main_analysis, new_main_analysis)
else:
    print("Warning: old_main_analysis not matched in main.py")

old_main_sort = """        # Filter out unrelated category jobs to ensure top recommended jobs are genuinely suitable
        compatible_jobs = [j for j in processed_jobs if not j.get("is_unrelated_domain", False)]
        display_dashboard_jobs = compatible_jobs if compatible_jobs else processed_jobs
        display_dashboard_jobs.sort(key=lambda j: (not j.get("is_unrelated_domain", False), j.get("combined_score", 0)), reverse=True)
        USER_JOBS_CACHE[current_user.id] = display_dashboard_jobs[:25]
        recommended_jobs = display_dashboard_jobs[:3]"""

new_main_sort = """        # Filter out unrelated category jobs to ensure top recommended jobs are genuinely suitable
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

if old_main_sort in main_code:
    main_code = main_code.replace(old_main_sort, new_main_sort)
else:
    print("Warning: old_main_sort not matched in main.py")

# Update render_template call in main.py
old_main_render = """    return render_template(
        "dashboard.html",
        resume=resume,
        candidate_profile=candidate_profile,
        saved_jobs=saved_jobs,
        extracted_skills_count=extracted_skills_count,
        top_match_score=top_match_score,
        recommended_jobs=recommended_jobs,
        skill_gap_summary=skill_gap_summary,
        pipeline_stats=pipeline_stats,
    )"""

new_main_render = """    return render_template(
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
    )"""

if old_main_render in main_code:
    main_code = main_code.replace(old_main_render, new_main_render)
else:
    print("Warning: old_main_render not matched in main.py")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_code)
print("main.py updated successfully.")

