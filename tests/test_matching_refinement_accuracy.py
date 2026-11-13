import pytest
from app.services.matcher import (
    extract_job_sections,
    extract_job_required_years,
    extract_experience_years,
    experience_relevance_score,
    education_qualification_score,
    project_portfolio_score,
    responsibilities_alignment_score,
    focused_semantic_score,
)
from app.services.skill_gap import (
    analyze_job_skill_gap,
    classify_job_skill_importance,
    evaluate_skill_evidence,
    RELATED_SKILL_MAP,
)


def test_classify_job_skill_importance():
    """
    Verifies that skills inside 'Requirements / Must-Have' sections are weighted higher (1.35x)
    than skills inside 'Preferred / Nice-to-Have' sections (0.70x).
    """
    job_desc = """
    Senior Python Backend Engineer
    RESPONSIBILITIES:
    - Build scalable microservices and RESTful APIs.
    - Write unit tests and maintain database schemas.
    REQUIREMENTS / MUST HAVE:
    - 5+ years of experience in Python and PostgreSQL.
    - Solid understanding of Docker and REST APIs.
    PREFERRED / NICE TO HAVE:
    - Experience with Kubernetes and GraphQL is a plus.
    - Familiarity with Redis is advantageous.
    """

    job_skills = ["Python", "PostgreSQL", "Docker", "REST API", "Kubernetes", "GraphQL", "Redis"]
    importance_map = classify_job_skill_importance(job_desc, job_skills)

    assert importance_map["python"]["importance"] == "required"
    assert importance_map["python"]["weight_mult"] == 1.35
    assert importance_map["postgresql"]["importance"] == "required"

    assert importance_map["kubernetes"]["importance"] == "preferred"
    assert importance_map["kubernetes"]["weight_mult"] == 0.70
    assert importance_map["graphql"]["importance"] == "preferred"
    assert importance_map["redis"]["importance"] == "preferred"


def test_required_skill_gap_impact_vs_preferred():
    """
    Missing a required core skill (e.g. Python for Python dev) must result in a lower
    score than missing an optional/preferred skill (e.g. GraphQL).
    """
    job_desc = """
    Python Backend Engineer
    REQUIREMENTS:
    - Strong proficiency in Python and PostgreSQL.
    NICE TO HAVE:
    - Experience with GraphQL and Redis.
    """

    # Candidate 1 has Python & PostgreSQL (all required skills), missing GraphQL & Redis (preferred)
    res_candidate1 = analyze_job_skill_gap(
        resume_skills=["Python", "PostgreSQL", "Git"],
        job_skills=["Python", "PostgreSQL", "GraphQL", "Redis"],
        resume_text="Backend developer experienced in Python and PostgreSQL.",
        job_description=job_desc,
        candidate_title="Backend Developer",
        job_title="Python Backend Engineer",
        candidate_domain="backend",
    )

    # Candidate 2 has GraphQL & Redis (preferred skills), missing Python & PostgreSQL (required)
    res_candidate2 = analyze_job_skill_gap(
        resume_skills=["GraphQL", "Redis", "Git"],
        job_skills=["Python", "PostgreSQL", "GraphQL", "Redis"],
        resume_text="Developer experienced in GraphQL and Redis.",
        job_description=job_desc,
        candidate_title="Backend Developer",
        job_title="Python Backend Engineer",
        candidate_domain="backend",
    )

    # Candidate 1 with required skills must score substantially higher than Candidate 2 missing required skills
    assert res_candidate1["final_score"] > res_candidate2["final_score"]
    assert res_candidate1["skill_coverage_score"] > res_candidate2["skill_coverage_score"]


def test_candidate_skill_evidence_depth():
    """
    Verifies that skills substantiated in work experience or projects receive depth recognition.
    """
    exp_text = "Senior Engineer at Acme Corp. Built low-latency REST APIs using Python and PostgreSQL."
    proj_text = "Real-time Chat App: Built messaging system with Redis and WebSockets."
    cv_text = f"EXPERIENCE\n{exp_text}\n\nPROJECTS\n{proj_text}"

    src_python, bonus_python = evaluate_skill_evidence("Python", ["Python", "PostgreSQL"], experience_text=exp_text, resume_text=cv_text)
    assert src_python == "Work Experience"
    assert bonus_python > 0

    src_redis, bonus_redis = evaluate_skill_evidence("Redis", ["Redis"], projects_text=proj_text, resume_text=cv_text)
    assert src_redis == "Practical Projects"
    assert bonus_redis > 0

    src_docker, bonus_docker = evaluate_skill_evidence("Docker", ["Docker"], experience_text="", projects_text="", resume_text="")
    assert src_docker == "Skills Summary"
    assert bonus_docker == 0.0


def test_expanded_transferable_skill_clusters():
    """
    Tests newly mapped industry clusters in RELATED_SKILL_MAP:
    Java <-> Spring Boot, C++ <-> Rust/C, Terraform <-> AWS/Ansible, Pytest <-> Unittest.
    """
    assert "spring boot" in RELATED_SKILL_MAP
    assert "Java" in RELATED_SKILL_MAP["spring boot"]["related"]

    assert "terraform" in RELATED_SKILL_MAP
    assert "AWS" in RELATED_SKILL_MAP["terraform"]["related"] or "DevOps" in RELATED_SKILL_MAP["terraform"]["related"]

    assert "pytest" in RELATED_SKILL_MAP
    assert "Python" in RELATED_SKILL_MAP["pytest"]["related"]

    # Java candidate evaluated for Spring Boot position gets partial transferable credit
    res_java = analyze_job_skill_gap(
        resume_skills=["Java", "SQL", "Git"],
        job_skills=["Spring Boot", "SQL", "Git"],
        candidate_title="Java Developer",
        job_title="Spring Boot Engineer",
        candidate_domain="backend",
    )
    partial_names = [p["skill"] for p in res_java["partial_skills"]]
    assert "Spring Boot" in partial_names
    sb_match = next(p for p in res_java["partial_skills"] if p["skill"] == "Spring Boot")
    assert sb_match["matched_via"] == "Java"
    assert sb_match["strength"] == "Partial Match"


def test_seniority_experience_penalty_and_reward():
    """
    Verifies that:
    1. A junior candidate (< 2 yrs) applying to a 7+ yr Principal Engineer job receives
       a calibrated experience penalty.
    2. A senior engineer applying to a senior role receives high tenure credit.
    3. An intern applying to an intern role receives high tenure credit.
    """
    principal_job = """
    Principal Software Architect
    Requirements:
    - 7+ years of experience leading complex distributed cloud systems.
    - Deep knowledge of microservices and system design.
    """

    intern_job = """
    Software Engineering Intern
    Requirements:
    - Currently enrolled in BS or MS in Computer Science.
    - Familiarity with Python or JavaScript.
    """

    junior_cv = """
    Junior Developer
    Experience: 1 year of software development experience at startup.
    Skills: Python, Git.
    """

    senior_cv = """
    Senior Architect
    Experience: 8+ years of experience architecting large scale cloud systems.
    Skills: Python, Microservices, Cloud.
    """

    # 1. Junior vs Principal
    exp_junior_principal = experience_relevance_score(junior_cv, principal_job)
    # 2. Senior vs Principal
    exp_senior_principal = experience_relevance_score(senior_cv, principal_job)

    assert exp_senior_principal >= 70
    assert exp_junior_principal < 45, f"Junior applying to 7+ yr Principal role must be penalized, got {exp_junior_principal}"

    # 3. Junior / Student vs Intern
    exp_junior_intern = experience_relevance_score(junior_cv, intern_job)
    assert exp_junior_intern >= 65, f"Junior/intern applicant should receive high fit for internship, got {exp_junior_intern}"


def test_project_portfolio_quantifiable_metrics_bonus():
    """
    Verifies that resumes demonstrating quantifiable metrics and live deployment links
    in projects receive higher portfolio scores.
    """
    plain_projects = """
    PROJECTS:
    - Note Taking App: Built a web app with React and Node.
    """

    metrics_projects = """
    PROJECTS:
    - High-Performance CDN: Built distributed caching layer with Redis and Go.
      Reduced latency by 45% and scaled to 50k requests/sec.
      Live demo: https://cdn-demo.vercel.app
    """

    job = "Software Engineer needing Go, Redis, and React."

    score_plain, _ = project_portfolio_score(plain_projects, job, projects_text=plain_projects)
    score_metrics, rationale = project_portfolio_score(metrics_projects, job, projects_text=metrics_projects)

    assert score_metrics > score_plain
    assert "Quantifiable engineering outcomes" in rationale or "live project demonstration" in rationale

