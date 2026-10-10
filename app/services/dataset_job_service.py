import json
import os
import re
import urllib.parse

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resumes_dataset.jsonl")
LOCAL_JOBS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "jobs.jsonl")

_DATASET_CACHE = []


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
                        jobs.append({
                            "job_title": item.get("title", "Software Developer"),
                            "employer_name": item.get("company", "Tech Corp"),
                            "company": item.get("company", "Tech Corp"),
                            "job_city": item.get("location", "Remote"),
                            "location": item.get("location", "Remote"),
                            "job_employment_type": item.get("employment_type", "Full-time"),
                            "job_description": item.get("description", ""),
                            "job_apply_link": f"https://www.google.com/search?q={urllib.parse.quote(item.get('title', '') + ' ' + item.get('company', '') + ' jobs')}",
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

                        job_item = {
                            "job_title": title,
                            "employer_name": company,
                            "company": company,
                            "job_city": "Remote",
                            "location": "Remote",
                            "job_employment_type": "Full-time",
                            "job_description": desc,
                            "job_apply_link": f"https://www.google.com/search?q={urllib.parse.quote(title + ' ' + company + ' jobs')}",
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
            "job_description": "Looking for an Android & Flutter Engineer with expertise in Kotlin, Jetpack Compose, Dart, REST APIs, MVVM Clean Architecture, and SQLite/Room.",
            "job_apply_link": "https://www.google.com/search?q=Android+Flutter+Developer+jobs",
            "job_skills": ["Android", "Flutter", "Kotlin", "Dart", "Jetpack Compose", "REST API", "MVVM"],
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
            "job_apply_link": "https://www.google.com/search?q=Python+Developer+Tech+Corp+jobs",
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
            "job_apply_link": "https://www.google.com/search?q=Machine+Learning+Engineer+Cognitive+AI+jobs",
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
            "job_apply_link": "https://www.google.com/search?q=Frontend+Engineer+Web+Solutions+jobs",
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
            "job_apply_link": "https://www.google.com/search?q=DevOps+Engineer+CloudScale+Systems+jobs",
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
