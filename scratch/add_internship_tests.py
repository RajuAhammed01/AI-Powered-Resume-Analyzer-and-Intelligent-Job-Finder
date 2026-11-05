test_file = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\tests\test_role_relevance.py"

with open(test_file, "r", encoding="utf-8") as f:
    text = f.read()

# Update top imports
old_imp = """from app.services.profile_detector import (
    detect_candidate_profile,
    classify_job_domain,
    is_job_domain_compatible,
)"""

new_imp = """from app.services.profile_detector import (
    detect_candidate_profile,
    classify_job_domain,
    is_job_domain_compatible,
    classify_job_seniority,
    detect_candidate_seniority_intent,
    get_job_ordering_tuple,
)"""

if old_imp in text:
    text = text.replace(old_imp, new_imp)
else:
    print("Warning: old_imp not matched")

new_tests = '''

def test_candidate_seniority_intent_detection():
    # 1. Detected via explicit preference
    intent_pref = detect_candidate_seniority_intent(experience_level_pref="Internship")
    assert intent_pref["is_internship_seeking"] is True
    assert intent_pref["preferred_seniority"] == "internship"

    # 2. Detected via declared title
    intent_title = detect_candidate_seniority_intent(declared_title="Computer Science Student")
    assert intent_title["is_internship_seeking"] is True

    # 3. Detected via resume student keywords
    student_cv = "Undergraduate student pursuing BS in Computer Science, expected graduation May 2026. Seeking software engineering internship."
    intent_cv = detect_candidate_seniority_intent(resume_text=student_cv)
    assert intent_cv["is_internship_seeking"] is True

    # 4. Experienced developer should not be classified as internship-seeking
    exp_cv = "Senior Software Engineer with 8 years of experience leading distributed cloud backend systems."
    intent_exp = detect_candidate_seniority_intent(resume_text=exp_cv, declared_title="Senior Engineer", experience_level_pref="Senior")
    assert intent_exp["is_internship_seeking"] is False
    assert intent_exp["preferred_seniority"] == "experienced"


def test_job_seniority_classification():
    # Internship
    info_intern = classify_job_seniority("Frontend Engineering Intern", "Summer 2026 internship opening")
    assert info_intern["is_internship"] is True
    assert info_intern["level"] == "internship"

    # Entry-level
    info_entry = classify_job_seniority("Junior Frontend Developer", "Entry level role for graduates")
    assert info_entry["is_entry_level"] is True
    assert info_entry["level"] == "entry_level"

    # Experienced
    info_exp = classify_job_seniority("Senior Frontend Engineer", "5+ years of experience required")
    assert info_exp["is_experienced"] is True
    assert info_exp["level"] == "experienced"


def test_internship_seeker_ordering_priority():
    """
    Verifies that for an internship-seeking candidate:
      1. Domain-compatible internships are ranked first (Tier 0).
      2. Domain-compatible entry-level positions follow next (Tier 1).
      3. Domain-compatible experienced positions follow (Tier 2).
      4. Unrelated internships (e.g. Marketing Intern) are demoted to Tier 3 and never prioritize ahead of tech jobs.
    """
    jobs = [
        {
            "job_title": "Marketing Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": True,  # Unrelated category
            "combined_score": 12,
        },
        {
            "job_title": "Senior Frontend Engineer",
            "is_internship": False,
            "is_entry_level": False,
            "is_unrelated_domain": False,
            "combined_score": 75,
        },
        {
            "job_title": "Frontend Engineering Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": False,
            "combined_score": 92,
        },
        {
            "job_title": "Junior Frontend Developer",
            "is_internship": False,
            "is_entry_level": True,
            "is_unrelated_domain": False,
            "combined_score": 88,
        },
        {
            "job_title": "React UI Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": False,
            "combined_score": 85,
        },
        {
            "job_title": "HR Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": True,  # Unrelated category
            "combined_score": 10,
        },
    ]

    # Sort with get_job_ordering_tuple for an internship seeker
    sorted_jobs = sorted(jobs, key=lambda j: get_job_ordering_tuple(j, is_internship_seeking=True))

    ordered_titles = [j["job_title"] for j in sorted_jobs]

    # 1. Tier 0: Relevant domain internships first (highest match score first)
    assert ordered_titles[0] == "Frontend Engineering Intern"
    assert ordered_titles[1] == "React UI Intern"

    # 2. Tier 1: Suitable domain entry-level positions
    assert ordered_titles[2] == "Junior Frontend Developer"

    # 3. Tier 2: Experienced domain positions
    assert ordered_titles[3] == "Senior Frontend Engineer"

    # 4. Tier 3: Incompatible / unrelated internships pushed to bottom
    assert ordered_titles[4] == "Marketing Intern"
    assert ordered_titles[5] == "HR Intern"


def test_unrelated_internship_is_penalized_for_tech_resume():
    """
    Ensure that an internship in an unrelated domain (e.g. Marketing Intern)
    is penalized with low match score (<= 18%) and flagged as unrelated domain,
    preventing it from ranking high simply because it has 'intern' in the title.
    """
    fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Git", "Communication"]
    fe_cv = "Computer Science student seeking web development internship. Proficient in React, JavaScript, HTML, CSS."

    res = analyze_job_skill_gap(
        resume_skills=fe_skills,
        job_skills=["Marketing", "Social Media", "Communication", "Git"],
        resume_text=fe_cv,
        job_description="Marketing Intern to manage social media and content marketing campaigns.",
        candidate_title="Frontend Intern",
        job_title="Marketing Intern",
        candidate_domain="frontend",
        is_internship_seeking=True,
    )

    assert res["is_unrelated_domain"] is True
    assert res["final_score"] <= 18
    assert "Unrelated Career Category" in res["summary_explanation"]
'''

if "test_candidate_seniority_intent_detection" not in text:
    text = text.rstrip() + "\n" + new_tests
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("test_role_relevance.py updated with internship tests.")
else:
    print("Tests already exist in test_role_relevance.py")

