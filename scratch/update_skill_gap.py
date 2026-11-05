import os

gap_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\skill_gap.py"

with open(gap_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update import from profile_detector
old_import = "from app.services.profile_detector import classify_job_domain, detect_candidate_profile, is_job_domain_compatible"
new_import = "from app.services.profile_detector import classify_job_domain, detect_candidate_profile, is_job_domain_compatible, classify_job_seniority"

if old_import in text:
    text = text.replace(old_import, new_import)
else:
    print("Warning: old_import string not found directly")

# 2. Update analyze_job_skill_gap signature
old_sig = """def analyze_job_skill_gap(
    resume_skills: list[str],
    job_skills: list[str],
    resume_text: str = "",
    job_description: str = "",
    candidate_title: str = "",
    job_title: str = "",
    experience_text: str = "",
    education_text: str = "",
    candidate_domain: str = "",
) -> dict:"""

new_sig = """def analyze_job_skill_gap(
    resume_skills: list[str],
    job_skills: list[str],
    resume_text: str = "",
    job_description: str = "",
    candidate_title: str = "",
    job_title: str = "",
    experience_text: str = "",
    education_text: str = "",
    candidate_domain: str = "",
    is_internship_seeking: bool = False,
    employment_type: str = "",
) -> dict:"""

if old_sig in text:
    text = text.replace(old_sig, new_sig)
else:
    print("Warning: old_sig not found directly")

# 3. Add seniority classification and internship scoring adjustments
old_domain_classify = """    # Classify job's career domain
    job_info = classify_job_domain(job_title, job_description, job_skills_clean)
    is_compatible, domain_mult, domain_expl = is_job_domain_compatible(candidate_domain, job_info["domain"])"""

new_domain_classify = """    # Classify job's career domain and seniority level
    job_info = classify_job_domain(job_title, job_description, job_skills_clean)
    is_compatible, domain_mult, domain_expl = is_job_domain_compatible(candidate_domain, job_info["domain"])
    seniority_info = classify_job_seniority(job_title, job_description, employment_type=employment_type)
    is_internship = seniority_info["is_internship"]
    is_entry_level = seniority_info["is_entry_level"]"""

if old_domain_classify in text:
    text = text.replace(old_domain_classify, new_domain_classify)
else:
    print("Warning: old_domain_classify not found directly")

# 4. Internship candidate adjustments to scores
old_comp_scores = """    # D) Experience Relevance (10%)
    experience_pct = experience_relevance_score(
        resume_text, job_description, experience_text
    ) if resume_text else 30

    # E) Education & Qualification (10%)
    education_pct = education_qualification_score(
        resume_text, job_description, education_text
    ) if resume_text else 20"""

new_comp_scores = """    # D) Experience Relevance (10%)
    experience_pct = experience_relevance_score(
        resume_text, job_description, experience_text
    ) if resume_text else 30

    # E) Education & Qualification (10%)
    education_pct = education_qualification_score(
        resume_text, job_description, education_text
    ) if resume_text else 20

    # F) Internship Alignment Adjustments for Early Career Seekers
    if is_compatible and is_internship_seeking and is_internship:
        # Credit academic coursework and technical project experience fully for internships
        experience_pct = max(80, experience_pct)
        education_pct = max(85, education_pct)
        title_pct = max(88, title_pct)
    elif is_compatible and is_internship_seeking and is_entry_level:
        experience_pct = max(70, experience_pct)
        education_pct = max(80, education_pct)
        title_pct = max(82, title_pct)"""

if old_comp_scores in text:
    text = text.replace(old_comp_scores, new_comp_scores)
else:
    print("Warning: old_comp_scores not found directly")

# 5. Update summary explanation for internships and return dict
old_expl = """    # ── 5. Human-readable explanation ─────────────────────────────────────
    if not is_compatible:
        cand_name = domain_cfg.get('name', candidate_domain)
        summary_explanation = (
            f"⚠️ Unrelated Career Category ({job_info['domain_name']} vs {cand_name}): "
            f"This role is outside your verified career discipline. Keyword overlaps (e.g. Git, Communication) "
            f"do not qualify as a high match. Match score heavily penalized to {final_score}%."
        )
    else:
        summary_explanation = (
            f"Your {final_score}% match is scored across 5 dimensions: "
            f"Weighted Skill Coverage {skill_coverage_pct}% ({skill_contrib} pts) + "
            f"Semantic Alignment {semantic_pct}% ({semantic_contrib} pts) + "
            f"Title & Domain Match {title_pct}% ({title_contrib} pts) + "
            f"Experience Fit {experience_pct}% ({experience_contrib} pts) + "
            f"Education {education_pct}% ({education_contrib} pts)."
        )"""

new_expl = """    # ── 5. Human-readable explanation ─────────────────────────────────────
    if not is_compatible:
        cand_name = domain_cfg.get('name', candidate_domain)
        summary_explanation = (
            f"⚠️ Unrelated Career Category ({job_info['domain_name']} vs {cand_name}): "
            f"This role is outside your verified career discipline. Keyword overlaps (such as 'intern' or common tools) "
            f"do not qualify as a high match. Match score heavily penalized to {final_score}%."
        )
    elif is_internship:
        summary_explanation = (
            f"🎓 Relevant Internship Match ({final_score}%): "
            f"Weighted Skill Coverage {skill_coverage_pct}% ({skill_contrib} pts) + "
            f"Semantic Alignment {semantic_pct}% ({semantic_contrib} pts) + "
            f"Title & Domain Match {title_pct}% ({title_contrib} pts) + "
            f"Academic & Project Fit {experience_pct}% ({experience_contrib} pts) + "
            f"Education {education_pct}% ({education_contrib} pts)."
        )
    else:
        summary_explanation = (
            f"Your {final_score}% match is scored across 5 dimensions: "
            f"Weighted Skill Coverage {skill_coverage_pct}% ({skill_contrib} pts) + "
            f"Semantic Alignment {semantic_pct}% ({semantic_contrib} pts) + "
            f"Title & Domain Match {title_pct}% ({title_contrib} pts) + "
            f"Experience Fit {experience_pct}% ({experience_contrib} pts) + "
            f"Education {education_pct}% ({education_contrib} pts)."
        )"""

if old_expl in text:
    text = text.replace(old_expl, new_expl)
else:
    print("Warning: old_expl not found directly")

# 6. Add seniority info to return dictionary
old_return = """        "is_unrelated_domain": not is_compatible,
        "domain_info": job_info,
        "domain_explanation": domain_expl,"""

new_return = """        "is_unrelated_domain": not is_compatible,
        "seniority_level": seniority_info["level"],
        "is_internship": seniority_info["is_internship"],
        "is_entry_level": seniority_info["is_entry_level"],
        "is_experienced": seniority_info["is_experienced"],
        "display_seniority": seniority_info["display_seniority"],
        "badge_color": seniority_info["badge_color"],
        "badge_bg": seniority_info["badge_bg"],
        "domain_info": job_info,
        "domain_explanation": domain_expl,"""

if old_return in text:
    text = text.replace(old_return, new_return)
else:
    print("Warning: old_return not found directly")

with open(gap_path, "w", encoding="utf-8") as f:
    f.write(text)

print("skill_gap.py updated successfully.")

