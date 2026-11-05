import pytest
from app.services.profile_detector import (
    detect_candidate_profile,
    classify_job_domain,
    is_job_domain_compatible,
    classify_job_seniority,
    detect_candidate_seniority_intent,
    get_job_ordering_tuple,
)
from app.services.skill_gap import analyze_job_skill_gap


def test_frontend_profile_detection():
    skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux"]
    profile = detect_candidate_profile(skills, declared_title="Frontend Developer")
    assert profile["primary_domain"] == "frontend"
    assert "Frontend Developer" in profile["search_queries"]
    assert "React Developer" in profile["search_queries"]


def test_data_ml_profile_detection():
    skills = ["Python", "Pandas", "scikit-learn", "PyTorch", "Machine Learning", "SQL"]
    profile = detect_candidate_profile(skills, declared_title="Machine Learning Engineer")
    assert profile["primary_domain"] == "data_ml"
    assert any(role in profile["search_queries"] for role in ["Machine Learning Engineer", "Data Scientist", "AI Engineer", "Data Analyst"])


def test_data_analyst_detection():
    skills = ["SQL", "Tableau", "Power BI", "Data Analysis", "Excel"]
    profile = detect_candidate_profile(skills, declared_title="Data Analyst")
    assert profile["primary_domain"] == "data_ml"
    assert profile["recommended_role"] == "Data Analyst"


def test_unrelated_non_tech_job_classification():
    non_tech_jobs = [
        "Freelance Copywriter",
        "Freelance Writer",
        "Content Writer",
        "Senior Sales Manager",
        "Academic Dean for MiaPrep Online Academy",
        "Remote Office Assistant",
        "Registered Nurse",
    ]
    for title in non_tech_jobs:
        info = classify_job_domain(title)
        assert info["domain"] == "unrelated_non_tech" or info["is_tech"] is False, f"Failed for title: {title}"


def test_network_engineer_is_unrelated_to_frontend():
    info = classify_job_domain("Network Engineer")
    assert info["domain"] == "networking_it"
    is_compat, mult, expl = is_job_domain_compatible("frontend", info["domain"])
    assert is_compat is False
    assert mult <= 0.15


def test_unrelated_writer_and_network_engineer_for_frontend():
    fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git", "Communication", "Problem Solving"]
    fe_text = "Frontend Developer skilled in React, JavaScript, HTML, CSS, Git, and Communication."

    unrelated_roles = [
        ("Freelance Writer", ["Writing", "Communication", "Research", "Git"]),
        ("Content Writer", ["Content", "Communication", "English", "Git"]),
        ("Network Engineer", ["Cisco", "TCP/IP", "Linux", "Git", "Communication", "Problem Solving"]),
    ]

    for title, job_skills in unrelated_roles:
        res = analyze_job_skill_gap(
            resume_skills=fe_skills,
            job_skills=job_skills,
            resume_text=fe_text,
            job_description=f"Hiring {title} with teamwork, git, and communication.",
            candidate_title="Frontend Developer",
            job_title=title,
            candidate_domain="frontend",
        )
        assert res["is_unrelated_domain"] is True, f"{title} should be marked unrelated"
        assert res["final_score"] <= 20, f"{title} score should be <= 20%, got {res['final_score']}%"


def test_frontend_resume_prioritizes_react_and_rejects_ml_and_sales():
    fe_skills = ["React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS", "Redux"]

    # 1. Matching React Developer role
    res_react = analyze_job_skill_gap(
        resume_skills=fe_skills,
        job_skills=["React", "JavaScript", "TypeScript"],
        candidate_title="Frontend Developer",
        job_title="Senior React Developer",
    )
    assert res_react["is_unrelated_domain"] is False
    assert res_react["final_score"] >= 65

    # 2. Unrelated ML role for frontend resume
    res_ml = analyze_job_skill_gap(
        resume_skills=fe_skills,
        job_skills=["Python", "Machine Learning", "PyTorch"],
        candidate_title="Frontend Developer",
        job_title="Machine Learning Engineer",
    )
    assert res_ml["is_unrelated_domain"] is True
    assert res_ml["final_score"] <= 20

    # 3. Non-tech sales role for frontend resume
    res_sales = analyze_job_skill_gap(
        resume_skills=fe_skills,
        job_skills=["Sales", "CRM"],
        candidate_title="Frontend Developer",
        job_title="Sales Manager",
    )
    assert res_sales["is_unrelated_domain"] is True
    assert res_sales["final_score"] <= 20


def test_ml_resume_prioritizes_ai_data_and_rejects_frontend():
    ml_skills = ["Python", "Pandas", "scikit-learn", "PyTorch", "Machine Learning", "SQL"]

    # 1. Matching ML Engineer role
    res_ml = analyze_job_skill_gap(
        resume_skills=ml_skills,
        job_skills=["Python", "Machine Learning", "PyTorch"],
        candidate_title="Machine Learning Engineer",
        job_title="Machine Learning Engineer",
    )
    assert res_ml["is_unrelated_domain"] is False
    assert res_ml["final_score"] >= 75

    # 2. Unrelated Frontend React role for ML resume
    res_fe = analyze_job_skill_gap(
        resume_skills=ml_skills,
        job_skills=["React", "CSS", "HTML"],
        candidate_title="Machine Learning Engineer",
        job_title="React Developer",
    )
    assert res_fe["is_unrelated_domain"] is True
    assert res_fe["final_score"] <= 20


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
