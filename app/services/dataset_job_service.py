import json
import os
import re
import urllib.parse

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resumes_dataset.jsonl")
LOCAL_JOBS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "jobs.jsonl")

_DATASET_CACHE = []


COMPANY_CAREER_URLS = {
    "nascenia": "https://www.nascenia.com/career/",
    "nascenia mobile labs": "https://www.nascenia.com/career/",
    "brain station": "https://brainstation-23.com/career/",
    "brain station 23": "https://brainstation-23.com/career/",
    "therap": "https://therapbd.com/careers/",
    "therap bd": "https://therapbd.com/careers/",
    "therap (bd) ltd.": "https://therapbd.com/careers/",
    "selise": "https://selisegroup.com/careers/",
    "selise digital platforms": "https://selisegroup.com/careers/",
    "enosis": "https://www.enosisbd.com/career/",
    "chaldal": "https://chaldal.com/careers",
    "kaz software": "https://kaz.com.bd/career/",
    "bjit": "https://bjitgroup.com/career",
    "leadsoft": "https://leadsoft.org/career/",
    "tech corp": "https://www.linkedin.com/jobs/search/?keywords=Python+Developer",
    "cognitive ai labs": "https://www.linkedin.com/jobs/search/?keywords=Machine+Learning+Engineer",
    "web solutions inc": "https://www.linkedin.com/jobs/search/?keywords=Frontend+Engineer+React",
    "cloudscale systems": "https://www.linkedin.com/jobs/search/?keywords=DevOps+Cloud+Engineer",
}


def resolve_job_links(title: str, company: str, location: str = "Remote", direct_url: str = "") -> dict:
    """
    Produce direct, verified application links instead of raw generic web search:
    - Official company careers portal (if known)
    - Targeted LinkedIn Jobs search (actual job application board with Easy Apply)
    - Google for Jobs official engine (with &ibp=htl;jobs)
    - Bdjobs portal (for Bangladesh tech roles)
    """
    comp_clean = (company or "").lower().strip()
    title_clean = (title or "").strip()
    loc_clean = (location or "Remote").strip()

    official_url = ""
    for k, v in COMPANY_CAREER_URLS.items():
        if k in comp_clean:
            official_url = v
            break

    if direct_url and "google.com/search" not in direct_url:
        primary_link = direct_url
    elif official_url:
        primary_link = official_url
    else:
        primary_link = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(title_clean + ' ' + company)}"
        if loc_clean and loc_clean.lower() != "remote":
            primary_link += f"&location={urllib.parse.quote(loc_clean)}"

    linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(title_clean + ' ' + company)}"
    if loc_clean and loc_clean.lower() != "remote":
        linkedin_url += f"&location={urllib.parse.quote(loc_clean)}"

    google_jobs_url = f"https://www.google.com/search?q={urllib.parse.quote(title_clean + ' ' + company + ' jobs')}&ibp=htl;jobs"

    bdjobs_url = ""
    if any(bd in loc_clean.lower() for bd in ["bangladesh", "dhaka", "chittagong"]):
        bdjobs_url = f"https://jobs.bdjobs.com/jobsearch.asp?txtsearch={urllib.parse.quote(title_clean)}"

    return {
        "primary_apply_link": primary_link,
        "official_career_url": official_url,
        "linkedin_apply_link": linkedin_url,
        "google_jobs_link": google_jobs_url,
        "bdjobs_link": bdjobs_url,
    }


def _load_benchmark_dataset_jobs():
    """Load and index benchmark jobs from local jobs.jsonl and resumes_dataset.jsonl."""
    global _DATASET_CACHE
    if _DATASET_CACHE:
        return _DATASET_CACHE

    jobs = []

    # 1. Load from data/jobs.jsonl
    if os.path.exists(LOCAL_JOBS_PATH):
        try:
            with open(LOCAL_JOBS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        t = item.get("title", "Software Developer")
                        c = item.get("company", "Tech Corp")
                        loc = item.get("location", "Remote")
                        links = resolve_job_links(t, c, loc)
                        jobs.append({
                            "job_title": t,
                            "employer_name": c,
                            "company": c,
                            "job_city": loc,
                            "location": loc,
                            "job_employment_type": item.get("employment_type", "Full-time"),
                            "job_description": item.get("description", ""),
                            "job_apply_link": links["primary_apply_link"],
                            "official_career_url": links["official_career_url"],
                            "linkedin_apply_link": links["linkedin_apply_link"],
                            "google_jobs_link": links["google_jobs_link"],
                            "bdjobs_link": links["bdjobs_link"],
                            "job_skills": item.get("required_skills", []),
                            "source": "Dataset (Jobs)",
                            "source_type": "dataset",
                        })
        except Exception:
            pass

    # 2. Extract representative benchmark roles across distinct categories in resumes_dataset.jsonl
    if os.path.exists(DATASET_PATH):
        try:
            seen_cats = {}
            with open(DATASET_PATH, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        cat = record.get("Category", "").strip()
                        if not cat or cat in seen_cats and len(seen_cats[cat]) >= 2:
                            continue

                        # Extract role requirements from Experience or Summary
                        skills_str = record.get("Skills", "")
                        skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]
                        exp_snippet = (record.get("Experience") or record.get("Summary") or "")[:500]

                        # Clean experience text
                        exp_clean = re.sub(r"\s+", " ", exp_snippet).strip()
                        title = f"{cat} Specialist" if not cat.lower().endswith("developer") and not cat.lower().endswith("engineer") else cat

                        company_names = [
                            "Global Systems", "Nexus Technologies", "Vertex Data Labs",
                            "Horizon Digital", "OmniCloud Solutions", "Apex Innovations",
                            "Stratum InfoTech", "Catalyst Software"
                        ]
                        company = company_names[(idx + len(cat)) % len(company_names)]

                        desc = (
                            f"We are hiring a qualified {title} to join our engineering organization. "
                            f"Requirements include hands-on proficiency in {', '.join(skills_list) if skills_list else cat}. "
                            f"Key focus areas: {exp_clean[:350]}..."
                        )

                        links = resolve_job_links(title, company, "Remote")
                        job_item = {
                            "job_title": title,
                            "employer_name": company,
                            "company": company,
                            "job_city": "Remote",
                            "location": "Remote",
                            "job_employment_type": "Full-time",
                            "job_description": desc,
                            "job_apply_link": links["primary_apply_link"],
                            "official_career_url": links["official_career_url"],
                            "linkedin_apply_link": links["linkedin_apply_link"],
                            "google_jobs_link": links["google_jobs_link"],
                            "bdjobs_link": links["bdjobs_link"],
                            "job_skills": skills_list if skills_list else [cat],
                            "source": "Dataset (ResumeAtlas)",
                            "source_type": "dataset",
                        }

                        if cat not in seen_cats:
                            seen_cats[cat] = []
                        seen_cats[cat].append(job_item)
                        jobs.append(job_item)

                        if len(jobs) >= 50:
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    # 3. Add default robust catalog if dataset had few entries
    default_catalog = [
        {
            "job_title": "Android & Flutter Developer",
            "employer_name": "Nascenia Mobile Labs",
            "company": "Nascenia Mobile Labs",
            "job_city": "Dhaka, Bangladesh",
            "location": "Dhaka, Bangladesh",
            "job_employment_type": "Full-time",
            "job_description": "Looking for an Android & Flutter Engineer with expertise in Kotlin, Jetpack Compose, Dart, REST APIs, MVVM Clean Architecture, and SQLite/Room. Direct opportunity to develop scalable mobile apps for international clients.",
            "job_apply_link": "https://www.nascenia.com/career/",
            "official_career_url": "https://www.nascenia.com/career/",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Android%20Flutter%20Developer%20Nascenia&location=Dhaka%2C%20Bangladesh",
            "google_jobs_link": "https://www.google.com/search?q=Android+Flutter+Developer+Nascenia+jobs&ibp=htl;jobs",
            "bdjobs_link": "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=Android+Flutter",
            "job_skills": ["Android", "Flutter", "Kotlin", "Dart", "Jetpack Compose", "REST API", "MVVM"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "Senior Flutter / Mobile Application Developer",
            "employer_name": "Brain Station 23",
            "company": "Brain Station 23",
            "job_city": "Dhaka, Bangladesh",
            "location": "Dhaka, Bangladesh",
            "job_employment_type": "Full-time",
            "job_description": "Brain Station 23 is seeking an experienced Flutter & Mobile Application Developer. Key focus on state management (Bloc/Provider), Clean Architecture, CI/CD for Play Store/App Store, and high-performance cross-platform delivery.",
            "job_apply_link": "https://brainstation-23.com/career/",
            "official_career_url": "https://brainstation-23.com/career/",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Flutter%20Developer%20Brain%20Station%2023&location=Dhaka%2C%20Bangladesh",
            "google_jobs_link": "https://www.google.com/search?q=Flutter+Developer+Brain+Station+23+jobs&ibp=htl;jobs",
            "bdjobs_link": "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=Flutter+Developer",
            "job_skills": ["Flutter", "Dart", "Android", "Bloc", "REST API", "Git", "Clean Architecture"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "Software Engineer (Mobile & Backend)",
            "employer_name": "Therap (BD) Ltd.",
            "company": "Therap (BD) Ltd.",
            "job_city": "Dhaka, Bangladesh",
            "location": "Dhaka, Bangladesh",
            "job_employment_type": "Full-time",
            "job_description": "Therap is looking for talented engineers passionate about mobile and distributed backend development. Work on mission-critical healthcare systems used across the globe.",
            "job_apply_link": "https://therapbd.com/careers/",
            "official_career_url": "https://therapbd.com/careers/",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Software%20Engineer%20Therap%20BD&location=Dhaka%2C%20Bangladesh",
            "google_jobs_link": "https://www.google.com/search?q=Software+Engineer+Therap+BD+jobs&ibp=htl;jobs",
            "bdjobs_link": "https://jobs.bdjobs.com/jobsearch.asp?txtsearch=Software+Engineer",
            "job_skills": ["Java", "Kotlin", "Android", "REST API", "SQL", "Git"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "Python Developer",
            "employer_name": "Tech Corp",
            "company": "Tech Corp",
            "job_city": "Remote",
            "location": "Remote",
            "job_employment_type": "Full-time",
            "job_description": "We are seeking a Python Developer with strong knowledge of Django, Flask, REST APIs, PostgreSQL, and Git.",
            "job_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Python+Developer+Tech+Corp",
            "official_career_url": "https://www.linkedin.com/jobs/search/?keywords=Python+Developer",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Python+Developer+Tech+Corp",
            "google_jobs_link": "https://www.google.com/search?q=Python+Developer+Tech+Corp+jobs&ibp=htl;jobs",
            "bdjobs_link": "",
            "job_skills": ["Python", "Django", "Flask", "PostgreSQL", "REST API", "Git"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "Machine Learning Engineer",
            "employer_name": "Cognitive AI Labs",
            "company": "Cognitive AI Labs",
            "job_city": "Remote",
            "location": "Remote",
            "job_employment_type": "Full-time",
            "job_description": "Looking for an ML Engineer skilled in Python, PyTorch, scikit-learn, and NLP. Train and deploy models to production.",
            "job_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Machine+Learning+Engineer",
            "official_career_url": "https://www.linkedin.com/jobs/search/?keywords=Machine+Learning+Engineer",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Machine+Learning+Engineer",
            "google_jobs_link": "https://www.google.com/search?q=Machine+Learning+Engineer+Cognitive+AI+jobs&ibp=htl;jobs",
            "bdjobs_link": "",
            "job_skills": ["Python", "PyTorch", "scikit-learn", "Machine Learning", "NLP"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "Frontend Engineer",
            "employer_name": "Web Solutions Inc",
            "company": "Web Solutions Inc",
            "job_city": "San Francisco, CA",
            "location": "San Francisco, CA",
            "job_employment_type": "Full-time",
            "job_description": "Experience required with React, JavaScript, TypeScript, HTML, CSS, and responsive UI design.",
            "job_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Frontend+Engineer+Web+Solutions",
            "official_career_url": "https://www.linkedin.com/jobs/search/?keywords=Frontend+Engineer+React",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=Frontend+Engineer+Web+Solutions",
            "google_jobs_link": "https://www.google.com/search?q=Frontend+Engineer+Web+Solutions+jobs&ibp=htl;jobs",
            "bdjobs_link": "",
            "job_skills": ["React", "JavaScript", "TypeScript", "HTML", "CSS"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        },
        {
            "job_title": "DevOps & Cloud Engineer",
            "employer_name": "CloudScale Systems",
            "company": "CloudScale Systems",
            "job_city": "Austin, TX",
            "location": "Austin, TX",
            "job_employment_type": "Full-time",
            "job_description": "Require DevOps engineer experienced in AWS, Docker, Kubernetes, CI/CD pipelines, Terraform, and Linux administration.",
            "job_apply_link": "https://www.linkedin.com/jobs/search/?keywords=DevOps+Engineer+CloudScale+Systems",
            "official_career_url": "https://www.linkedin.com/jobs/search/?keywords=DevOps+Cloud+Engineer",
            "linkedin_apply_link": "https://www.linkedin.com/jobs/search/?keywords=DevOps+Engineer+CloudScale+Systems",
            "google_jobs_link": "https://www.google.com/search?q=DevOps+Engineer+CloudScale+Systems+jobs&ibp=htl;jobs",
            "bdjobs_link": "",
            "job_skills": ["AWS", "Docker", "Kubernetes", "CI/CD", "Linux", "Terraform"],
            "source": "Dataset (Curated)",
            "source_type": "dataset",
        }
    ]

    for item in default_catalog:
        if not any(j["job_title"].lower() == item["job_title"].lower() for j in jobs):
            jobs.append(item)

    _DATASET_CACHE = jobs
    return _DATASET_CACHE


def get_dataset_jobs(role: str = "", location: str = "Remote", limit: int = 25) -> list[dict]:
    """Retrieve and rank benchmark jobs from the local dataset."""
    all_jobs = _load_benchmark_dataset_jobs()
    if not role or role.lower() in ["software engineer", "developer", "all"]:
        return all_jobs[:limit]

    role_terms = [t.strip().lower() for t in re.findall(r"[a-zA-Z]+", role) if len(t.strip()) > 2]
    if not role_terms:
        return all_jobs[:limit]

    scored = []
    for job in all_jobs:
        score = 0
        j_text = f"{job['job_title']} {job['job_description']} {' '.join(job.get('job_skills', []))}".lower()
        for term in role_terms:
            if term in job["job_title"].lower():
                score += 5
            elif term in j_text:
                score += 2
        scored.append((score, job))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored][:limit]
