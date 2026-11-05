skill_gap_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\skill_gap.py"

with open(skill_gap_path, "r", encoding="utf-8") as f:
    text = f.read()

old_block = """    # B) Required Qualifications & Education (15%)
    qualifications_pct = education_qualification_score(
        resume_text, job_description, education_text=education_text
    ) if resume_text else 30

    # C) Professional Experience Relevance (15%)
    experience_pct = experience_relevance_score(
        resume_text, job_description, experience_text=experience_text
    ) if resume_text else 30

    # D) Practical Projects & Portfolio Implementation (15%)
    projects_pct, projects_rationale = project_portfolio_score(
        resume_text=resume_text,
        job_description=job_description,
        projects_text=projects_text,
        job_skills=job_skills_clean,
        is_internship_seeking=is_internship_seeking,
    ) if resume_text else (25, "No practical project portfolio detected.")

    # E) Job Responsibilities & Day-to-Day Tasks (10%)
    responsibilities_pct, responsibilities_rationale = responsibilities_alignment_score(
        resume_text=resume_text,
        job_description=job_description,
        experience_text=experience_text,
        projects_text=projects_text,
    ) if resume_text else (40, "General task alignment.")"""

new_block = """    # B) Required Qualifications & Education (15%)
    qualifications_pct = education_qualification_score(
        resume_text, job_description, education_text=education_text
    ) if (resume_text and job_description) else (70 if is_compatible else 20)

    # C) Professional Experience Relevance (15%)
    experience_pct = experience_relevance_score(
        resume_text, job_description, experience_text=experience_text
    ) if (resume_text and job_description) else (70 if is_compatible else 20)

    # D) Practical Projects & Portfolio Implementation (15%)
    projects_pct, projects_rationale = project_portfolio_score(
        resume_text=resume_text,
        job_description=job_description,
        projects_text=projects_text,
        job_skills=job_skills_clean,
        is_internship_seeking=is_internship_seeking,
    ) if (resume_text and job_description) else ((70, "Relevant technical skills in candidate profile.") if is_compatible else (15, "No domain project alignment."))

    # E) Job Responsibilities & Day-to-Day Tasks (10%)
    responsibilities_pct, responsibilities_rationale = responsibilities_alignment_score(
        resume_text=resume_text,
        job_description=job_description,
        experience_text=experience_text,
        projects_text=projects_text,
    ) if (resume_text and job_description) else ((70, "Role duties align with declared candidate profile.") if is_compatible else (20, "Unrelated job duties."))"""

if old_block in text:
    text = text.replace(old_block, new_block)
    with open(skill_gap_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("skill_gap.py updated with baseline handling.")
else:
    print("Warning: old_block not found in skill_gap.py")

