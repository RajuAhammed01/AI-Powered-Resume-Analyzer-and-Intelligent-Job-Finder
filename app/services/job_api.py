import os
import time
import requests
import urllib.parse

from app.services.job_scraper import scrape_live_jobs
from app.services.dataset_job_service import get_dataset_jobs

_CACHE = {}
CACHE_TTL = 1800  # 30 minutes


def fetch_jobs(role: str = "", location: str = "Remote", source: str = "all") -> list[dict]:
    """
    Hybrid Job Recommender Orchestrator.
    Combines Real-Time Web Scraping (RemoteOK, Remotive) and Local Dataset Matching (ResumeAtlas, jobs.jsonl).
    Both systems work seamlessly without conflict.

    :param role: Target job role or search query (e.g. 'Android Developer', 'Python')
    :param location: Location preference (e.g. 'Remote', 'Dhaka, Bangladesh')
    :param source: 'all' (both), 'web' (live web scraped only), or 'dataset' (dataset only)
    :return: List of normalized job dictionaries
    """
    clean_role = (role or "Software Engineer").strip()
    clean_loc = (location or "Remote").strip()
    clean_source = (source or "all").lower().strip()

    cache_key = f"{clean_role}_{clean_loc}_{clean_source}".lower()

    # 1. Check in-memory cache
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data

    # Optional RapidAPI JSearch if user provided an API key in .env
    api_key = os.getenv("JSEARCH_API_KEY")
    api_jobs = []
    if api_key and api_key not in ["your_key_here", "your_jsearch_api_key_here", ""]:
        try:
            resp = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
                params={"query": f"{clean_role} in {clean_loc}", "page": "1", "num_pages": "1"},
                timeout=8,
            )
            if resp.ok:
                raw_data = resp.json().get("data", [])
                for item in raw_data:
                    api_jobs.append({
                        "job_title": item.get("job_title", clean_role),
                        "employer_name": item.get("employer_name", "Tech Company"),
                        "company": item.get("employer_name", "Tech Company"),
                        "job_city": item.get("job_city") or item.get("job_country") or clean_loc,
                        "location": item.get("job_city") or item.get("job_country") or clean_loc,
                        "job_employment_type": item.get("job_employment_type", "Full-time"),
                        "job_description": item.get("job_description", "")[:1200],
                        "job_apply_link": item.get("job_apply_link") or f"https://www.google.com/search?q={urllib.parse.quote(clean_role + ' jobs')}",
                        "job_skills": [],
                        "source": "RapidAPI JSearch",
                        "source_type": "web",
                    })
        except Exception:
            pass

    # 2. Fetch based on source parameter
    scraped_jobs = []
    dataset_jobs = []

    if clean_source in ["all", "web"]:
        try:
            scraped_jobs = scrape_live_jobs(role=clean_role, location=clean_loc, limit=15)
        except Exception:
            scraped_jobs = []

    if clean_source in ["all", "dataset"] or (clean_source == "web" and not scraped_jobs and not api_jobs):
        try:
            dataset_jobs = get_dataset_jobs(role=clean_role, location=clean_loc, limit=15)
        except Exception:
            dataset_jobs = []

    # 3. Merge & Deduplicate
    final_jobs = []
    seen = set()

    # Prioritize API jobs first if configured
    for job in api_jobs:
        key = (job.get("job_title", "").lower().strip(), (job.get("employer_name") or job.get("company", "")).lower().strip())
        if key not in seen:
            seen.add(key)
            final_jobs.append(job)

    # Next add Live Web Scraped jobs
    for job in scraped_jobs:
        key = (job.get("job_title", "").lower().strip(), (job.get("employer_name") or job.get("company", "")).lower().strip())
        if key not in seen:
            seen.add(key)
            final_jobs.append(job)

    # Then add Dataset Benchmark jobs
    for job in dataset_jobs:
        key = (job.get("job_title", "").lower().strip(), (job.get("employer_name") or job.get("company", "")).lower().strip())
        if key not in seen:
            seen.add(key)
            final_jobs.append(job)

    # If both returned nothing (extreme edge case), fallback to standard dataset
    if not final_jobs:
        final_jobs = get_dataset_jobs(role="Software Engineer", location="Remote", limit=10)

    _CACHE[cache_key] = (final_jobs, time.time())
    return final_jobs
