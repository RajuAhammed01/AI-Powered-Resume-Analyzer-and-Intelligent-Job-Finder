import pytest
from app.services.skill_gap import analyze_job_skill_gap, normalize_skill_name
from app.services.matcher import title_alignment_score


def test_canonical_skill_synonym_normalization():
    """Verify that common tech variations normalize to canonical representations."""
    assert normalize_skill_name("React.js") == "react"
    assert normalize_skill_name("ReactJS") == "react"
    assert normalize_skill_name("Postgres") == "postgresql"
    assert normalize_skill_name("PostgreSQL") == "postgresql"
    assert normalize_skill_name("PSQL") == "postgresql"
    assert normalize_skill_name("K8s") == "kubernetes"
    assert normalize_skill_name("Kubernetes") == "kubernetes"
    assert normalize_skill_name("Fast API") == "fastapi"
    assert normalize_skill_name("FastAPI") == "fastapi"
    assert normalize_skill_name("fast-api") == "fastapi"
    assert normalize_skill_name("Amazon Web Services") == "aws"
    assert normalize_skill_name("AWS") == "aws"
    assert normalize_skill_name("RESTful APIs") == "rest apis"
    assert normalize_skill_name("REST APIs") == "rest apis"
    assert normalize_skill_name("REST API") == "rest apis"
    assert normalize_skill_name("Node.js") == "node.js"
    assert normalize_skill_name("NodeJS") == "node.js"
    assert normalize_skill_name("Golang") == "go"
    assert normalize_skill_name("Go") == "go"
    assert normalize_skill_name("Scikit-Learn") == "scikit-learn"
    assert normalize_skill_name("sklearn") == "scikit-learn"


def test_skill_matching_with_punctuation_and_synonym_variants():
    """
    Candidate with standard framework names matches job requirements written with
    differing punctuation, spacing, and industry aliases.
    """
    candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "REST APIs"]
    job_skills = ["Python", "Fast API", "Postgres", "Amazon Web Services", "Docker", "RESTful APIs", "K8s"]

    resume_text = (
        "Experienced Backend Developer.\n\n"
        "Education:\n"
        "Bachelor of Science in Computer Science\n\n"
        "Work Experience:\n"
        "Backend Developer (4+ years of experience).\n"
        "Built robust web services using Python, FastAPI, and PostgreSQL. "
        "Containerized microservices with Docker and deployed to Amazon Web Services (AWS) using REST APIs.\n\n"
        "Projects:\n"
        "Cloud API Platform: Developed microservices with FastAPI, PostgreSQL, and Docker. "
        "Scaled architecture on AWS, reduced latency by 35% for 50,000 requests."
    )
    job_desc = (
        "Requirements:\n"
        "- Strong experience with Python and Fast API\n"
        "- Proficient in Postgres and Docker\n"
        "- Experience with Amazon Web Services and RESTful APIs\n"
        "- Familiarity with K8s cluster deployments is a plus\n"
        "- Bachelor's degree in Computer Science or related field\n"
        "- 3+ years of experience in backend development\n"
    )

    analysis = analyze_job_skill_gap(
        resume_skills=candidate_skills,
        job_skills=job_skills,
        resume_text=resume_text,
        job_description=job_desc,
        candidate_title="Backend Developer",
        job_title="Python Backend Engineer",
        candidate_domain="backend",
    )

    # All core requirements should match strongly or partially
    strong_skill_names = [s["skill"].lower() for s in analysis["strong_skills"]]
    partial_skill_names = [s["skill"].lower() for s in analysis["partial_skills"]]

    assert "python" in strong_skill_names
    assert "fast api" in strong_skill_names
    assert "postgres" in strong_skill_names
    assert "amazon web services" in strong_skill_names
    assert "docker" in strong_skill_names
    assert "restful apis" in strong_skill_names
    assert "k8s" in partial_skill_names

    # The candidate is well-matched
    assert analysis["skill_coverage_score"] >= 90
    assert analysis["final_score"] >= 80


def test_direct_resume_text_skill_presence_fallback():
    """
    If a skill wasn't in the explicit parsed skills list but is documented in the candidate's
    experience/project text, the matching engine accurately credits it.
    """
    # Candidate skills list is incomplete
    candidate_skills = ["Python", "Django"]
    job_skills = ["Python", "Django", "Redis", "Celery"]

    resume_text = (
        "Software Engineer. Architected high-throughput asynchronous task processing pipeline "
        "leveraging Celery workers and in-memory caching with Redis."
    )
    job_desc = (
        "Requirements:\n"
        "- Python, Django, Redis, and Celery background task processing\n"
    )

    analysis = analyze_job_skill_gap(
        resume_skills=candidate_skills,
        job_skills=job_skills,
        resume_text=resume_text,
        job_description=job_desc,
        candidate_title="Backend Developer",
        job_title="Python Developer",
        candidate_domain="backend",
    )

    strong_skill_names = [s["skill"].lower() for s in analysis["strong_skills"]]
    assert "redis" in strong_skill_names
    assert "celery" in strong_skill_names
    assert analysis["skill_coverage_score"] >= 90


def test_title_alignment_fixed_unreachable_code_and_equivalence():
    """Verify title alignment logic correctly scales by domain compatibility and handles equivalent titles."""
    # 1. Developer vs Engineer with junior qualifier
    score_eng = title_alignment_score("Junior Backend Developer", "Junior Backend Engineer", candidate_domain="backend", job_domain="backend")
    assert score_eng >= 88

    # 2. Same domain high alignment
    score_same_domain = title_alignment_score("Software Engineer", "Backend Engineer", candidate_domain="backend", job_domain="backend")
    assert score_same_domain >= 80

    # 3. Unrelated career domain strictly penalized
    score_unrelated = title_alignment_score("Machine Learning Engineer", "Sales Associate", candidate_domain="data_ml", job_domain="sales_marketing")
    assert score_unrelated <= 15
