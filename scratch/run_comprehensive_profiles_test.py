import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
from app.services.profile_detector import (
    detect_candidate_profile,
    classify_job_domain,
    is_job_domain_compatible,
    detect_candidate_seniority_intent,
    classify_job_seniority,
    get_job_ordering_tuple,
)
from app.services.skill_gap import analyze_job_skill_gap
from app.services.job_validator import (
    normalize_apply_url,
    is_valid_apply_url,
    generate_job_id,
    ensure_job_identity,
    find_job_by_identifier,
)

print("=" * 70)
print("COMPREHENSIVE TESTING: THREE PROFESSIONAL PROFILES")
print("=" * 70)

# =========================================================================
# PROFILE 1: FRONTEND DEVELOPER
# =========================================================================
print("\n--- [PROFILE 1: FRONTEND DEVELOPER] ---")
fe_skills = ["React", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"]
fe_cv_text = """
Alex Rivers - Frontend Developer
Passionate Frontend Developer with 3 years of experience building accessible, responsive, and performant web applications using React, TypeScript, and modern CSS frameworks.
Experience:
- Frontend Engineer at PixelCraft: Developed high-traffic component libraries in React, TypeScript, and Tailwind CSS. Integrated REST and GraphQL APIs.
- Web Developer at CodeForge: Built single-page web applications with Redux state management and responsive CSS.
Education:
Bachelor of Science in Computer Science, University of Technology, 2021.
Projects:
- E-Commerce UI Storefront: Built full shopping cart with React 18, TypeScript, and Tailwind CSS.
"""

fe_profile = detect_candidate_profile(fe_skills, fe_cv_text, declared_title="Frontend Developer")
print(f"Detected Profile Domain: {fe_profile['primary_domain']} ({fe_profile['domain_name']})")
print(f"Recommended Role: {fe_profile['recommended_role']}")
print(f"Search Queries: {fe_profile['search_queries']}")

assert fe_profile["primary_domain"] == "frontend"
assert fe_profile["recommended_role"] in ["Frontend Developer", "React Developer"]

# Test Frontend Job Pool
fe_job_pool = [
    {
        "job_title": "Senior React Developer",
        "employer_name": "Vercel",
        "job_apply_link": "https://vercel.com/careers/sr-react",
        "job_skills": ["React", "TypeScript", "Next.js", "CSS3", "HTML5"],
        "job_description": "We are seeking a Senior React Developer proficient in React, TypeScript, and modern CSS to build scalable web applications.",
    },
    {
        "job_title": "Frontend Engineer",
        "employer_name": "Stripe",
        "job_apply_link": "https://stripe.com/jobs/frontend-engineer",
        "job_skills": ["JavaScript", "React", "HTML5", "CSS3", "Git"],
        "job_description": "Frontend Engineer to build interactive payment interfaces with React and JavaScript.",
    },
    {
        "job_title": "Vue.js UI Developer",
        "employer_name": "GitLab",
        "job_apply_link": "https://gitlab.com/jobs/vue-developer",
        "job_skills": ["Vue.js", "JavaScript", "HTML5", "CSS3"],
        "job_description": "UI Developer experienced in modern component frameworks such as Vue or React.",
    },
    {
        "job_title": "Network Engineer",
        "employer_name": "Cisco Systems",
        "job_apply_link": "https://cisco.com/jobs/network-eng",
        "job_skills": ["Cisco", "TCP/IP", "BGP", "Linux", "Git"],
        "job_description": "Manage enterprise network infrastructure, routers, and firewalls.",
    },
    {
        "job_title": "Freelance Content Writer",
        "employer_name": "BlogMedia",
        "job_apply_link": "https://blogmedia.com/careers/writer",
        "job_skills": ["Content Writing", "SEO", "Communication", "English"],
        "job_description": "Produce engaging blog posts and marketing articles.",
    },
    {
        "job_title": "Data Analyst",
        "employer_name": "FinAnalytics",
        "job_apply_link": "https://finanalytics.com/jobs/data-analyst",
        "job_skills": ["SQL", "Tableau", "Power BI", "Excel"],
        "job_description": "Analyze financial metrics and build Tableau dashboards.",
    },
]

print("\nEvaluating Frontend Candidate against Job Pool:")
scored_fe_jobs = []
for job in fe_job_pool:
    analysis = analyze_job_skill_gap(
        resume_skills=fe_skills,
        job_skills=job["job_skills"],
        resume_text=fe_cv_text,
        job_description=job["job_description"],
        candidate_title="Frontend Developer",
        job_title=job["job_title"],
        candidate_domain="frontend",
    )
    job.update({
        "combined_score": analysis["final_score"],
        "is_unrelated_domain": analysis["is_unrelated_domain"],
        "matched_skills": analysis["matched_skills"],
        "partial_skills": analysis["partial_skills"],
        "missing_skills": analysis["missing_skills"],
        "explanation": analysis["summary_explanation"],
    })
    scored_fe_jobs.append(job)
    print(f" -> '{job['job_title']}': Score = {job['combined_score']}%, Unrelated = {job['is_unrelated_domain']}, Matched = {job['matched_skills']}, Partial = {[p['skill'] for p in job['partial_skills']]}")

# Verify Frontend results
react_job = next(j for j in scored_fe_jobs if "React" in j["job_title"])
net_job = next(j for j in scored_fe_jobs if "Network" in j["job_title"])
writer_job = next(j for j in scored_fe_jobs if "Writer" in j["job_title"])
data_job = next(j for j in scored_fe_jobs if "Data Analyst" in j["job_title"])

assert react_job["combined_score"] >= 70, f"React score should be >= 70, got {react_job['combined_score']}"
assert net_job["is_unrelated_domain"] is True, "Network Engineer must be unrelated"
assert net_job["combined_score"] <= 18, f"Network Engineer score should be <= 18, got {net_job['combined_score']}"
assert writer_job["is_unrelated_domain"] is True, "Content Writer must be unrelated"
assert writer_job["combined_score"] <= 15, f"Content Writer score should be <= 15, got {writer_job['combined_score']}"
assert data_job["is_unrelated_domain"] is True, "Data Analyst must be unrelated to Frontend profile"
assert data_job["combined_score"] <= 18, f"Data Analyst score should be <= 18, got {data_job['combined_score']}"
print("[PASS] Profile 1 (Frontend Developer) verified successfully!")


# =========================================================================
# PROFILE 2: DATA ANALYST
# =========================================================================
print("\n--- [PROFILE 2: DATA ANALYST] ---")
da_skills = ["SQL", "Tableau", "Power BI", "Excel", "Python", "Pandas", "Data Analysis", "Data Visualization", "Statistics"]
da_cv_text = """
Priya Sharma - Data Analyst
Results-driven Data Analyst with 3 years of experience transforming complex datasets into actionable business insights.
Experience:
- Data Analyst at MetroAnalytics: Designed and maintained executive KPI dashboards in Tableau and Power BI. Wrote complex SQL queries to extract data from PostgreSQL and Snowflake.
- Junior Business Analyst at GlobalTech: Automated monthly reporting using Excel, Python (Pandas), and SQL. Performed exploratory data analysis and statistical reporting.
Education:
Bachelor of Science in Statistics and Information Systems, 2021.
Projects:
- Customer Churn Dashboard: Developed interactive Tableau dashboard analyzing customer retention.
- Sales Forecasting Model: Used Python and Pandas to analyze quarterly sales trends.
"""

da_profile = detect_candidate_profile(da_skills, da_cv_text, declared_title="Data Analyst")
print(f"Detected Profile Domain: {da_profile['primary_domain']} ({da_profile['domain_name']})")
print(f"Recommended Role: {da_profile['recommended_role']}")
print(f"Search Queries: {da_profile['search_queries']}")

assert da_profile["primary_domain"] == "data_ml"
assert da_profile["recommended_role"] == "Data Analyst"

# Test Data Analyst Job Pool
da_job_pool = [
    {
        "job_title": "Senior Data Analyst",
        "employer_name": "Spotify",
        "job_apply_link": "https://spotify.com/jobs/sr-data-analyst",
        "job_skills": ["SQL", "Tableau", "Python", "Data Analysis", "Statistics"],
        "job_description": "We are seeking a Senior Data Analyst to analyze listener behavior, build Tableau dashboards, and query relational databases with SQL.",
    },
    {
        "job_title": "Business Intelligence Analyst",
        "employer_name": "Amazon",
        "job_apply_link": "https://amazon.jobs/bi-analyst",
        "job_skills": ["Power BI", "SQL", "Excel", "Data Visualization"],
        "job_description": "BI Analyst to develop Power BI reports, maintain automated metrics, and communicate insights to leadership.",
    },
    {
        "job_title": "Machine Learning Engineer",
        "employer_name": "OpenAI",
        "job_apply_link": "https://openai.com/careers/mle",
        "job_skills": ["PyTorch", "Deep Learning", "CUDA", "C++", "Distributed Systems"],
        "job_description": "Train large language models using distributed PyTorch and optimize CUDA kernels.",
    },
    {
        "job_title": "Frontend React Developer",
        "employer_name": "Airbnb",
        "job_apply_link": "https://airbnb.com/careers/frontend",
        "job_skills": ["React", "JavaScript", "CSS3", "HTML5", "Redux"],
        "job_description": "Build responsive booking web interfaces using React and modern CSS.",
    },
    {
        "job_title": "Technical Content Writer",
        "employer_name": "TechPubs",
        "job_apply_link": "https://techpubs.com/jobs/writer",
        "job_skills": ["Content Writing", "Documentation", "Communication"],
        "job_description": "Write technical blog posts and API user guides.",
    },
]

print("\nEvaluating Data Analyst Candidate against Job Pool:")
scored_da_jobs = []
for job in da_job_pool:
    analysis = analyze_job_skill_gap(
        resume_skills=da_skills,
        job_skills=job["job_skills"],
        resume_text=da_cv_text,
        job_description=job["job_description"],
        candidate_title="Data Analyst",
        job_title=job["job_title"],
        candidate_domain="data_ml",
    )
    job.update({
        "combined_score": analysis["final_score"],
        "is_unrelated_domain": analysis["is_unrelated_domain"],
        "matched_skills": analysis["matched_skills"],
        "partial_skills": analysis["partial_skills"],
        "missing_skills": analysis["missing_skills"],
        "explanation": analysis["summary_explanation"],
    })
    scored_da_jobs.append(job)
    print(f" -> '{job['job_title']}': Score = {job['combined_score']}%, Unrelated = {job['is_unrelated_domain']}, Matched = {job['matched_skills']}, Missing = {job['missing_skills']}")

# Verify Data Analyst results
spotify_job = next(j for j in scored_da_jobs if "Senior Data Analyst" in j["job_title"])
bi_job = next(j for j in scored_da_jobs if "Business Intelligence" in j["job_title"])
mle_job = next(j for j in scored_da_jobs if "Machine Learning" in j["job_title"])
fe_airbnb_job = next(j for j in scored_da_jobs if "Frontend" in j["job_title"])
writer_da_job = next(j for j in scored_da_jobs if "Content Writer" in j["job_title"])

assert spotify_job["combined_score"] >= 75, f"Senior Data Analyst should score >= 75, got {spotify_job['combined_score']}"
assert bi_job["combined_score"] >= 70, f"BI Analyst should score >= 70, got {bi_job['combined_score']}"
# ML Engineer requires deep learning/pytorch which candidate lacks, so score must be significantly lower than Data Analyst
assert mle_job["combined_score"] < spotify_job["combined_score"], "ML Engineer must score lower than Data Analyst for Data Analyst profile"
assert fe_airbnb_job["is_unrelated_domain"] is True, "Frontend React role must be unrelated to Data Analyst profile"
assert fe_airbnb_job["combined_score"] <= 18, f"Frontend score should be <= 18, got {fe_airbnb_job['combined_score']}"
assert writer_da_job["is_unrelated_domain"] is True, "Writer must be unrelated to Data Analyst profile"
assert writer_da_job["combined_score"] <= 15, f"Writer score should be <= 15, got {writer_da_job['combined_score']}"
print("[PASS] Profile 2 (Data Analyst) verified successfully!")


# =========================================================================
# PROFILE 3: MACHINE LEARNING ENGINEER
# =========================================================================
print("\n--- [PROFILE 3: MACHINE LEARNING ENGINEER] ---")
mle_skills = ["Python", "PyTorch", "TensorFlow", "scikit-learn", "Deep Learning", "Machine Learning", "NLP", "Docker", "SQL", "MLOps"]
mle_cv_text = """
Marcus Chen - Machine Learning Engineer
AI & Machine Learning Engineer with 4 years of experience designing, training, and deploying production deep learning models and NLP pipelines.
Experience:
- Senior ML Engineer at Cerebrum AI: Architected Transformer-based NLP pipelines using PyTorch and Hugging Face. Deployed containerized models with Docker and FastAPI.
- Machine Learning Engineer at DataWave: Trained computer vision and predictive models using TensorFlow and scikit-learn. Implemented automated MLOps CI/CD pipelines.
Education:
Master of Science in Computer Science (Artificial Intelligence specialization), Stanford University, 2020.
Projects:
- Multi-Modal Search Engine: Built vector embeddings retrieval pipeline using PyTorch and FAISS.
- Real-Time Fraud Detection: Deployed gradient boosted decision trees and deep learning models handling 10k req/sec.
"""

mle_profile = detect_candidate_profile(mle_skills, mle_cv_text, declared_title="Machine Learning Engineer")
print(f"Detected Profile Domain: {mle_profile['primary_domain']} ({mle_profile['domain_name']})")
print(f"Recommended Role: {mle_profile['recommended_role']}")
print(f"Search Queries: {mle_profile['search_queries']}")

assert mle_profile["primary_domain"] == "data_ml"
assert mle_profile["recommended_role"] in ["Machine Learning Engineer", "AI Engineer"]

# Test ML Engineer Job Pool
mle_job_pool = [
    {
        "job_title": "Machine Learning Engineer",
        "employer_name": "Anthropic",
        "job_apply_link": "https://anthropic.com/careers/mle",
        "job_skills": ["Python", "PyTorch", "Deep Learning", "NLP", "Docker"],
        "job_description": "We are looking for a Machine Learning Engineer with deep PyTorch experience to train LLMs and scale inference pipelines.",
    },
    {
        "job_title": "AI Research Engineer",
        "employer_name": "Google DeepMind",
        "job_apply_link": "https://deepmind.google/careers/ai-engineer",
        "job_skills": ["Python", "TensorFlow", "Deep Learning", "Machine Learning"],
        "job_description": "Research and engineer scalable deep learning models in TensorFlow and JAX.",
    },
    {
        "job_title": "React Frontend Developer",
        "employer_name": "WebFlow",
        "job_apply_link": "https://webflow.com/jobs/react-dev",
        "job_skills": ["React", "JavaScript", "HTML5", "CSS3"],
        "job_description": "Develop visual design canvas using React and client-side JavaScript.",
    },
    {
        "job_title": "Sales Account Executive",
        "employer_name": "SalesPro",
        "job_apply_link": "https://salespro.com/jobs/ae",
        "job_skills": ["Sales", "B2B", "CRM", "Cold Calling"],
        "job_description": "Drive enterprise B2B sales quota and qualify leads.",
    },
    {
        "job_title": "Network Administrator",
        "employer_name": "Telecom Corp",
        "job_apply_link": "https://telecom.com/jobs/netadmin",
        "job_skills": ["Cisco", "TCP/IP", "VPN", "Firewalls"],
        "job_description": "Configure routers, switches, and corporate LAN/WAN connectivity.",
    },
]

print("\nEvaluating ML Engineer Candidate against Job Pool:")
scored_mle_jobs = []
for job in mle_job_pool:
    analysis = analyze_job_skill_gap(
        resume_skills=mle_skills,
        job_skills=job["job_skills"],
        resume_text=mle_cv_text,
        job_description=job["job_description"],
        candidate_title="Machine Learning Engineer",
        job_title=job["job_title"],
        candidate_domain="data_ml",
    )
    job.update({
        "combined_score": analysis["final_score"],
        "is_unrelated_domain": analysis["is_unrelated_domain"],
        "matched_skills": analysis["matched_skills"],
        "partial_skills": analysis["partial_skills"],
        "missing_skills": analysis["missing_skills"],
        "explanation": analysis["summary_explanation"],
    })
    scored_mle_jobs.append(job)
    print(f" -> '{job['job_title']}': Score = {job['combined_score']}%, Unrelated = {job['is_unrelated_domain']}, Matched = {job['matched_skills']}, Missing = {job['missing_skills']}")

anthropic_job = next(j for j in scored_mle_jobs if "Anthropic" in j["employer_name"])
deepmind_job = next(j for j in scored_mle_jobs if "DeepMind" in j["employer_name"])
react_mle_job = next(j for j in scored_mle_jobs if "React" in j["job_title"])
sales_mle_job = next(j for j in scored_mle_jobs if "Sales" in j["job_title"])
net_mle_job = next(j for j in scored_mle_jobs if "Network" in j["job_title"])

assert anthropic_job["combined_score"] >= 80, f"Anthropic MLE should score >= 80, got {anthropic_job['combined_score']}"
assert deepmind_job["combined_score"] >= 75, f"DeepMind AI Engineer should score >= 75, got {deepmind_job['combined_score']}"
assert react_mle_job["is_unrelated_domain"] is True, "React must be unrelated to ML Engineer profile"
assert react_mle_job["combined_score"] <= 18, f"React score should be <= 18, got {react_mle_job['combined_score']}"
assert sales_mle_job["is_unrelated_domain"] is True, "Sales must be unrelated to ML Engineer profile"
assert sales_mle_job["combined_score"] <= 15, f"Sales score should be <= 15, got {sales_mle_job['combined_score']}"
assert net_mle_job["is_unrelated_domain"] is True, "Network must be unrelated to ML Engineer profile"
assert net_mle_job["combined_score"] <= 18, f"Network score should be <= 18, got {net_mle_job['combined_score']}"
print("[PASS] Profile 3 (Machine Learning Engineer) verified successfully!")


# =========================================================================
# INTERNSHIP PRIORITIZATION ACROSS PROFILES
# =========================================================================
print("\n--- [INTERNSHIP PRIORITIZATION VERIFICATION] ---")

# Test 1: Frontend Intern Seeker
intern_cv = "Undergraduate student graduating May 2026 pursuing BS in Computer Science. Seeking summer frontend development internship."
intent = detect_candidate_seniority_intent(resume_text=intern_cv, declared_title="Frontend Developer Intern")
assert intent["is_internship_seeking"] is True

intern_job_pool = [
    {
        "job_title": "Marketing Intern",
        "is_internship": True,
        "is_entry_level": False,
        "is_unrelated_domain": True,  # Unrelated
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
]

sorted_intern_jobs = sorted(intern_job_pool, key=lambda j: get_job_ordering_tuple(j, is_internship_seeking=True))
titles = [j["job_title"] for j in sorted_intern_jobs]
print(f"Internship seeker sorted order: {titles}")
assert titles[0] == "Frontend Engineering Intern", "Domain internship must be 1st"
assert titles[1] == "Junior Frontend Developer", "Entry-level must be 2nd"
assert titles[2] == "Senior Frontend Engineer", "Experienced must be 3rd"
assert titles[3] == "Marketing Intern", "Unrelated internship must be last"
print("[PASS] Internship prioritization verified!")

print("\n" + "=" * 70)
print("ALL PROFILE TESTS PASSED WITH 100% SUCCESS!")
print("=" * 70)
