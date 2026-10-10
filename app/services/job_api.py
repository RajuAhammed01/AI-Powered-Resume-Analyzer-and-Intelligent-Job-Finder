import os
import requests
import time
import urllib.parse

_CACHE = {}
CACHE_TTL = 3600  # 1 hour

FALLBACK_JOBS_CATALOG = [
    {
        "job_title": "Python Developer",
        "employer_name": "Tech Corp",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "We are seeking a Python Developer with strong knowledge of Django, REST APIs, PostgreSQL, and Git. Experience with Docker and automated testing is a plus.",
        "job_apply_link": "https://www.google.com/search?q=Python+Developer+Tech+Corp+jobs"
    },
    {
        "job_title": "Machine Learning Engineer",
        "employer_name": "Cognitive AI Labs",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "Looking for an ML Engineer skilled in Python, PyTorch, scikit-learn, and NLP. You will design, train, and deploy machine learning models to production.",
        "job_apply_link": "https://www.google.com/search?q=Machine+Learning+Engineer+Cognitive+AI+jobs"
    },
    {
        "job_title": "Data Analyst",
        "employer_name": "DataWorks Analytics",
        "job_city": "New York, NY",
        "job_employment_type": "Full-time",
        "job_description": "Seeking a Data Analyst proficient in SQL, Pandas, Excel, and Power BI or Tableau. Must possess strong communication and dashboard storytelling skills.",
        "job_apply_link": "https://www.google.com/search?q=Data+Analyst+DataWorks+Analytics+jobs"
    },
    {
        "job_title": "Frontend Engineer",
        "employer_name": "Web Solutions Inc",
        "job_city": "San Francisco, CA",
        "job_employment_type": "Full-time",
        "job_description": "Experience required with React, JavaScript, TypeScript, HTML, CSS, and responsive UI design. Knowledge of Next.js and Tailwind is a strong bonus.",
        "job_apply_link": "https://www.google.com/search?q=Frontend+Engineer+Web+Solutions+jobs"
    },
    {
        "job_title": "Full Stack Developer",
        "employer_name": "Innovate Software",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "Hiring a Full Stack Developer experienced in Node.js, Python, React, and MongoDB. Responsible for developing end-to-end web applications and microservices.",
        "job_apply_link": "https://www.google.com/search?q=Full+Stack+Developer+Innovate+Software+jobs"
    },
    {
        "job_title": "DevOps Engineer",
        "employer_name": "CloudScale Systems",
        "job_city": "Austin, TX",
        "job_employment_type": "Full-time",
        "job_description": "Require DevOps engineer experienced in AWS, Docker, Kubernetes, CI/CD pipelines, Terraform, and Linux administration.",
        "job_apply_link": "https://www.google.com/search?q=DevOps+Engineer+CloudScale+Systems+jobs"
    },
    {
        "job_title": "Data Scientist",
        "employer_name": "Insight Metrics",
        "job_city": "Remote",
        "job_employment_type": "Contract",
        "job_description": "Need a Data Scientist skilled in Python, statistics, NumPy, Pandas, predictive modeling, and data visualization. Experience with BigQuery is desirable.",
        "job_apply_link": "https://www.google.com/search?q=Data+Scientist+Insight+Metrics+jobs"
    },
    {
        "job_title": "Software Engineer (Backend)",
        "employer_name": "Apex Digital",
        "job_city": "Chicago, IL",
        "job_employment_type": "Full-time",
        "job_description": "Apex Digital is hiring a Backend Software Engineer. Must know Java, Spring Boot, or Python Flask, relational databases, and microservices architecture.",
        "job_apply_link": "https://www.google.com/search?q=Software+Engineer+Apex+Digital+jobs"
    },
    {
        "job_title": "AI & NLP Research Engineer",
        "employer_name": "NeuralTech Global",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "Seeking an AI Research Engineer specialized in Large Language Models (LLMs), Transformers, PyTorch, Hugging Face, and semantic search systems.",
        "job_apply_link": "https://www.google.com/search?q=AI+NLP+Research+Engineer+NeuralTech+jobs"
    },
    {
        "job_title": "Junior Web Developer",
        "employer_name": "PixelCraft Studios",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "Great opportunity for junior developers! Experience with HTML5, CSS3, JavaScript, Git, and basic backend concepts. Eager to learn and grow.",
        "job_apply_link": "https://www.google.com/search?q=Junior+Web+Developer+PixelCraft+jobs"
    }
]

def _get_curated_fallback(role: str, location: str):
    role_terms = [t.strip().lower() for t in role.replace(",", " ").split() if len(t.strip()) > 2]
    
    if not role_terms:
        return FALLBACK_JOBS_CATALOG

    scored = []
    for job in FALLBACK_JOBS_CATALOG:
        score = 0
        job_text = f"{job['job_title']} {job['job_description']}".lower()
        for term in role_terms:
            if term in job_text:
                score += 2
            if term in job["job_title"].lower():
                score += 3
        scored.append((score, job))

    # Sort so most relevant fallback jobs come first
    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored]


def fetch_jobs(role, location):
    cache_key = f"{role}_{location}".lower()
    
    # Check cache
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data

    api_key = os.getenv("JSEARCH_API_KEY")
    if not api_key or api_key in ["your_key_here", "your_jsearch_api_key_here", ""]:
        fallback = _get_curated_fallback(role or "Software Engineer", location or "Remote")
        _CACHE[cache_key] = (fallback, time.time())
        return fallback

    try:
        response = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={"query": f"{role} in {location}", "page": "1", "num_pages": "1"},
            timeout=15,
        )
        if response.ok:
            data = response.json().get("data", [])
            if data:
                _CACHE[cache_key] = (data, time.time())
                return data
    except Exception:
        pass
        
    fallback = _get_curated_fallback(role or "Software Engineer", location or "Remote")
    _CACHE[cache_key] = (fallback, time.time())
    return fallback
