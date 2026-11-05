import json
import pytest

from app import create_app
from app.extensions import db
from app.models import JobPreference, Resume, SavedJob, User
from app.routes.jobs import USER_JOBS_CACHE
from app.services.profile_detector import (
    detect_candidate_profile,
    detect_candidate_seniority_intent,
    get_job_ordering_tuple,
)
from app.services.skill_gap import analyze_job_skill_gap
from app.services.job_validator import (
    GLOBAL_JOBS_REGISTRY,
    ensure_job_identity,
    find_job_by_identifier,
    is_valid_apply_url,
    normalize_apply_url,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# =========================================================================
# 1. FRONTEND DEVELOPER PROFILE TESTS
# =========================================================================
def test_frontend_profile_recommendation_and_ranking():
    fe_skills = ["React", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"]
    fe_cv = """
    Alex Rivers - Frontend Developer
    Passionate Frontend Developer with 3 years of experience building accessible, responsive, and performant web applications using React, TypeScript, and modern CSS frameworks.
    Experience:
    - Frontend Engineer at PixelCraft (2022 - Present): Developed high-traffic component libraries in React, TypeScript, and Tailwind CSS. Integrated REST and GraphQL APIs.
    - Web Developer at CodeForge (2021 - 2022): Built single-page web applications with Redux state management and responsive CSS.
    Education:
    Bachelor of Science in Computer Science, University of Technology, 2021.
    Projects:
    - E-Commerce UI Storefront: Built full shopping cart with React 18, TypeScript, and Tailwind CSS.
    """

    profile = detect_candidate_profile(fe_skills, fe_cv, declared_title="Frontend Developer")
    assert profile["primary_domain"] == "frontend"
    assert profile["recommended_role"] in ["Frontend Developer", "React Developer"]

    jobs = [
        {
            "job_title": "Senior React Developer",
            "employer_name": "Vercel",
            "job_apply_link": "https://vercel.com/careers/senior-react",
            "job_skills": ["React", "TypeScript", "Next.js", "CSS3", "HTML5"],
            "job_description": "We are seeking a Senior React Developer proficient in React, TypeScript, and modern CSS to build scalable web applications.",
        },
        {
            "job_title": "Network Engineer",
            "employer_name": "Cisco",
            "job_apply_link": "https://cisco.com/jobs/network",
            "job_skills": ["Cisco", "TCP/IP", "BGP", "Linux", "Git"],
            "job_description": "Network Engineer managing switches, routers, and enterprise network infrastructure.",
        },
        {
            "job_title": "Freelance Writer",
            "employer_name": "ContentHub",
            "job_apply_link": "https://contenthub.com/careers/writer",
            "job_skills": ["Writing", "SEO", "Communication", "English"],
            "job_description": "Write engaging articles, blog posts, and marketing content.",
        },
    ]

    scored = []
    for j in jobs:
        analysis = analyze_job_skill_gap(
            resume_skills=fe_skills,
            job_skills=j["job_skills"],
            resume_text=fe_cv,
            job_description=j["job_description"],
            candidate_title="Frontend Developer",
            job_title=j["job_title"],
            candidate_domain="frontend",
        )
        j["combined_score"] = analysis["final_score"]
        j["is_unrelated_domain"] = analysis["is_unrelated_domain"]
        j["matched_skills"] = analysis["matched_skills"]
        j["partial_skills"] = analysis["partial_skills"]
        j["missing_skills"] = analysis["missing_skills"]
        scored.append(j)

    react_job = next(j for j in scored if "React" in j["job_title"])
    net_job = next(j for j in scored if "Network" in j["job_title"])
    writer_job = next(j for j in scored if "Writer" in j["job_title"])

    # High match for React, low for unrelated
    assert react_job["combined_score"] >= 70, f"React score should be >= 70, got {react_job['combined_score']}"
    assert react_job["is_unrelated_domain"] is False
    assert "React" in react_job["matched_skills"]

    assert net_job["is_unrelated_domain"] is True
    assert net_job["combined_score"] <= 18

    assert writer_job["is_unrelated_domain"] is True
    assert writer_job["combined_score"] <= 15


# =========================================================================
# 2. DATA ANALYST PROFILE TESTS
# =========================================================================
def test_data_analyst_profile_recommendation_and_ranking():
    da_skills = ["SQL", "Tableau", "Power BI", "Excel", "Python", "Pandas", "Data Analysis", "Statistics"]
    da_cv = """
    Priya Sharma - Data Analyst
    Results-driven Data Analyst with 3 years of experience transforming complex datasets into actionable business insights.
    Experience:
    - Data Analyst at MetroAnalytics (2022 - Present): Designed and maintained executive KPI dashboards in Tableau and Power BI. Wrote complex SQL queries to extract data from PostgreSQL and Snowflake.
    - Junior Business Analyst at GlobalTech (2021 - 2022): Automated monthly reporting using Excel, Python (Pandas), and SQL. Performed exploratory data analysis and statistical reporting.
    Education:
    Bachelor of Science in Statistics and Information Systems, 2021.
    Projects:
    - Customer Churn Dashboard: Developed interactive Tableau dashboard analyzing customer retention.
    - Sales Forecasting Model: Used Python and Pandas to analyze quarterly sales trends.
    """

    profile = detect_candidate_profile(da_skills, da_cv, declared_title="Data Analyst")
    assert profile["primary_domain"] == "data_ml"
    assert profile["recommended_role"] == "Data Analyst"
    assert "Data Analyst" in profile["search_queries"]

    jobs = [
        {
            "job_title": "Senior Data Analyst",
            "employer_name": "Spotify",
            "job_apply_link": "https://spotify.com/jobs/sr-analyst",
            "job_skills": ["SQL", "Tableau", "Python", "Data Analysis", "Statistics"],
            "job_description": "We are seeking a Senior Data Analyst to analyze listener behavior, build Tableau dashboards, and query relational databases with SQL.",
        },
        {
            "job_title": "Business Intelligence Analyst",
            "employer_name": "Amazon",
            "job_apply_link": "https://amazon.jobs/bi-analyst",
            "job_skills": ["Power BI", "SQL", "Excel", "Data Analysis"],
            "job_description": "BI Analyst to develop Power BI reports, maintain automated metrics, and communicate insights to leadership.",
        },
        {
            "job_title": "React Frontend Developer",
            "employer_name": "WebLab",
            "job_apply_link": "https://weblab.io/jobs/fe",
            "job_skills": ["React", "JavaScript", "HTML5", "CSS3"],
            "job_description": "Develop client-facing web application interfaces in React.",
        },
        {
            "job_title": "Content Writer",
            "employer_name": "Media Corp",
            "job_apply_link": "https://media.com/jobs/writer",
            "job_skills": ["Copywriting", "SEO", "Communication"],
            "job_description": "Write technical blogs, marketing articles, and customer newsletters.",
        },
    ]

    scored = []
    for j in jobs:
        analysis = analyze_job_skill_gap(
            resume_skills=da_skills,
            job_skills=j["job_skills"],
            resume_text=da_cv,
            job_description=j["job_description"],
            candidate_title="Data Analyst",
            job_title=j["job_title"],
            candidate_domain="data_ml",
        )
        j["combined_score"] = analysis["final_score"]
        j["is_unrelated_domain"] = analysis["is_unrelated_domain"]
        j["matched_skills"] = analysis["matched_skills"]
        scored.append(j)

    da_job = next(j for j in scored if "Data Analyst" in j["job_title"])
    bi_job = next(j for j in scored if "Business Intelligence" in j["job_title"])
    fe_job = next(j for j in scored if "Frontend" in j["job_title"])
    writer_job = next(j for j in scored if "Content Writer" in j["job_title"])

    assert da_job["combined_score"] >= 75, f"Data Analyst score should be >= 75, got {da_job['combined_score']}"
    assert da_job["is_unrelated_domain"] is False
    assert "SQL" in da_job["matched_skills"]
    assert "Tableau" in da_job["matched_skills"]

    assert bi_job["combined_score"] >= 70, f"BI Analyst score should be >= 70, got {bi_job['combined_score']}"
    assert bi_job["is_unrelated_domain"] is False

    assert fe_job["is_unrelated_domain"] is True
    assert fe_job["combined_score"] <= 18

    assert writer_job["is_unrelated_domain"] is True
    assert writer_job["combined_score"] <= 15


# =========================================================================
# 3. MACHINE LEARNING ENGINEER PROFILE TESTS
# =========================================================================
def test_ml_engineer_profile_recommendation_and_ranking():
    mle_skills = ["Python", "PyTorch", "TensorFlow", "scikit-learn", "Deep Learning", "Machine Learning", "NLP", "Docker"]
    mle_cv = """
    Marcus Chen - Machine Learning Engineer
    AI & Machine Learning Engineer with 4 years of experience designing, training, and deploying production deep learning models and NLP pipelines.
    Experience:
    - Senior ML Engineer at Cerebrum AI (2022 - Present): Architected Transformer-based NLP pipelines using PyTorch and Hugging Face. Deployed containerized models with Docker and FastAPI.
    - Machine Learning Engineer at DataWave (2020 - 2022): Trained computer vision and predictive models using TensorFlow and scikit-learn. Implemented automated MLOps CI/CD pipelines.
    Education:
    Master of Science in Computer Science (Artificial Intelligence specialization), Stanford University, 2020.
    Projects:
    - Multi-Modal Search Engine: Built vector embeddings retrieval pipeline using PyTorch and FAISS.
    - Real-Time Fraud Detection: Deployed gradient boosted decision trees and deep learning models handling 10k req/sec.
    """

    profile = detect_candidate_profile(mle_skills, mle_cv, declared_title="Machine Learning Engineer")
    assert profile["primary_domain"] == "data_ml"
    assert profile["recommended_role"] in ["Machine Learning Engineer", "AI Engineer"]

    jobs = [
        {
            "job_title": "Machine Learning Engineer",
            "employer_name": "Anthropic",
            "job_apply_link": "https://anthropic.com/careers/mle",
            "job_skills": ["Python", "PyTorch", "Deep Learning", "NLP", "Docker"],
            "job_description": "We are looking for a Machine Learning Engineer with deep PyTorch experience to train LLMs and scale inference pipelines.",
        },
        {
            "job_title": "Frontend React Engineer",
            "employer_name": "SaaS Co",
            "job_apply_link": "https://saasco.com/jobs/react",
            "job_skills": ["React", "CSS3", "JavaScript"],
            "job_description": "Build interactive user dashboards with React.",
        },
        {
            "job_title": "Corporate Sales Representative",
            "employer_name": "SalesForce Org",
            "job_apply_link": "https://salesforceorg.com/jobs/sales",
            "job_skills": ["Sales", "B2B", "CRM"],
            "job_description": "Generate sales pipeline and execute enterprise agreements.",
        },
    ]

    scored = []
    for j in jobs:
        analysis = analyze_job_skill_gap(
            resume_skills=mle_skills,
            job_skills=j["job_skills"],
            resume_text=mle_cv,
            job_description=j["job_description"],
            candidate_title="Machine Learning Engineer",
            job_title=j["job_title"],
            candidate_domain="data_ml",
        )
        j["combined_score"] = analysis["final_score"]
        j["is_unrelated_domain"] = analysis["is_unrelated_domain"]
        j["matched_skills"] = analysis["matched_skills"]
        scored.append(j)

    mle_job = next(j for j in scored if "Machine Learning" in j["job_title"])
    fe_job = next(j for j in scored if "Frontend" in j["job_title"])
    sales_job = next(j for j in scored if "Sales" in j["job_title"])

    assert mle_job["combined_score"] >= 80, f"MLE score should be >= 80, got {mle_job['combined_score']}"
    assert mle_job["is_unrelated_domain"] is False
    assert "PyTorch" in mle_job["matched_skills"]
    assert "Deep Learning" in mle_job["matched_skills"]

    assert fe_job["is_unrelated_domain"] is True
    assert fe_job["combined_score"] <= 18

    assert sales_job["is_unrelated_domain"] is True
    assert sales_job["combined_score"] <= 15


# =========================================================================
# 4. INTERNSHIP PRIORITIZATION ACROSS PROFILES
# =========================================================================
def test_internship_prioritization_across_profiles():
    # Intern-seeking candidate
    intern_intent = detect_candidate_seniority_intent(
        resume_text="Computer Science student expecting graduation May 2026. Seeking software engineering internship.",
        declared_title="Software Intern",
    )
    assert intern_intent["is_internship_seeking"] is True

    mixed_jobs = [
        {
            "job_title": "HR Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": True,  # Unrelated category
            "combined_score": 10,
        },
        {
            "job_title": "Senior Software Architect",
            "is_internship": False,
            "is_entry_level": False,
            "is_unrelated_domain": False,
            "combined_score": 85,
        },
        {
            "job_title": "Software Engineering Intern",
            "is_internship": True,
            "is_entry_level": False,
            "is_unrelated_domain": False,
            "combined_score": 90,
        },
        {
            "job_title": "Junior Software Engineer",
            "is_internship": False,
            "is_entry_level": True,
            "is_unrelated_domain": False,
            "combined_score": 87,
        },
    ]

    sorted_for_intern = sorted(mixed_jobs, key=lambda j: get_job_ordering_tuple(j, is_internship_seeking=True))
    titles = [j["job_title"] for j in sorted_for_intern]

    assert titles[0] == "Software Engineering Intern", "Relevant domain internship must be 1st"
    assert titles[1] == "Junior Software Engineer", "Relevant entry-level must be 2nd"
    assert titles[2] == "Senior Software Architect", "Experienced must be 3rd"
    assert titles[3] == "HR Intern", "Unrelated internship must be last (demoted to Tier 3)"


# =========================================================================
# 5. END-TO-END APPLY NOW REDIRECT & PIPELINE TRACKING TEST
# =========================================================================
def test_end_to_end_apply_now_workflow(app, client):
    # Setup test candidate in database
    user = User(name="Elena Rostova", email="elena@example.com", title_role="Data Analyst")
    user.set_password("SecurePass123!")
    db.session.add(user)
    db.session.commit()

    resume = Resume(
        user_id=user.id,
        filename="elena_data_analyst.pdf",
        extracted_skills=json.dumps(["SQL", "Tableau", "Power BI", "Excel", "Python", "Data Analysis"]),
        extracted_text="Elena Rostova. Experienced Data Analyst specializing in SQL, Tableau, and Power BI.",
    )
    pref = JobPreference(user_id=user.id, target_role="Data Analyst", location="Remote")
    db.session.add(resume)
    db.session.add(pref)
    db.session.commit()

    # Log in
    client.post("/login", data={"email": "elena@example.com", "password": "SecurePass123!"})

    # Prepare recommended job with authentic URL
    authentic_job = {
        "job_title": "Senior Data Analyst",
        "company": "Netflix",
        "employer_name": "Netflix",
        "job_city": "Los Gatos, CA",
        "job_employment_type": "Full-time",
        "job_apply_link": "https://jobs.netflix.com/jobs/889900/senior-data-analyst",
        "combined_score": 88,
        "job_skills": ["SQL", "Tableau", "Python"],
    }
    ensure_job_identity(authentic_job)
    authentic_job["cache_id"] = 0
    USER_JOBS_CACHE[user.id] = [authentic_job]

    # Candidate clicks Apply Now
    resp = client.get(f"/job/apply/{authentic_job['job_id']}")
    assert resp.status_code == 302
    assert resp.location == "https://jobs.netflix.com/jobs/889900/senior-data-analyst"

    # Verify pipeline auto-tracking in SavedJob table
    saved = SavedJob.query.filter_by(user_id=user.id, company="Netflix").first()
    assert saved is not None
    assert saved.status == "Applied"
    assert saved.job_title == "Senior Data Analyst"
    assert saved.apply_link == "https://jobs.netflix.com/jobs/889900/senior-data-analyst"
    assert saved.match_score == 88
