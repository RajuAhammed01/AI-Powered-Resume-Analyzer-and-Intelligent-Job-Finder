import logging
import os
import time
import urllib.parse
import requests

from app.services.job_validator import (
    normalize_apply_url,
    is_valid_apply_url,
    generate_job_id,
    GLOBAL_JOBS_REGISTRY,
)
from app.services.job_scraper import (
    scrape_live_jobs,
    scrape_remotive,
    scrape_arbeitnow,
    scrape_remoteok,
    scrape_jobicy,
)

logger = logging.getLogger(__name__)

_CACHE = {}
CACHE_TTL = 900  # 15 minutes


def fetch_adzuna_jobs(role: str, location: str, limit: int = 15) -> list[dict]:
    """Fetch live jobs from Adzuna API if ADZUNA_APP_ID & ADZUNA_APP_KEY are configured."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key or app_id.startswith("your_") or app_key.startswith("your_"):
        return []

    jobs = []
    try:
        country = "us"
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": limit,
            "what": role,
            "where": location if location and location.lower() != "remote" else "",
            "content-type": "application/json",
        }
        resp = requests.get(url, params=params, timeout=7)
        if resp.ok:
            data = resp.json().get("results", [])
            for item in data:
                title = item.get("title", "")
                company = (item.get("company") or {}).get("display_name", "Hiring Employer")
                apply_link = item.get("redirect_url")
                if not apply_link or not title:
                    continue

                location_name = (item.get("location") or {}).get("display_name", location or "Remote")
                desc = item.get("description", "")
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_str = f"${salary_min:,.0f} - ${salary_max:,.0f}" if salary_min and salary_max else ""

                jobs.append({
                    "job_title": title,
                    "employer_name": company,
                    "company": company,
                    "job_city": location_name,
                    "location": location_name,
                    "job_employment_type": "Full-time",
                    "job_description": desc[:1400],
                    "job_apply_link": apply_link,
                    "job_skills": [],
                    "salary": salary_str,
                    "source": "Adzuna",
                    "source_type": "web",
                    "publication_date": item.get("created", ""),
                })
    except Exception as e:
        logger.warning(f"Adzuna fetch error: {e}")
    return jobs


def fetch_jsearch_jobs(role: str, location: str, limit: int = 15) -> list[dict]:
    """Fetch live jobs from RapidAPI JSearch if JSEARCH_API_KEY is configured."""
    api_key = os.getenv("JSEARCH_API_KEY")
    if not api_key or api_key in ["your_key_here", "your_jsearch_api_key_here", ""]:
        return []

    jobs = []
    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={"query": f"{role} in {location}", "page": "1", "num_pages": "1"},
            timeout=8,
        )
        if resp.ok:
            raw_data = resp.json().get("data", [])
            for item in raw_data:
                apply_link = item.get("job_apply_link")
                if not apply_link:
                    continue
                jobs.append({
                    "job_title": item.get("job_title", role),
                    "employer_name": item.get("employer_name", "Tech Company"),
                    "company": item.get("employer_name", "Tech Company"),
                    "job_city": item.get("job_city") or item.get("job_country") or location,
                    "location": item.get("job_city") or item.get("job_country") or location,
                    "job_employment_type": item.get("job_employment_type", "Full-time"),
                    "job_description": item.get("job_description", "")[:1400],
                    "job_apply_link": apply_link,
                    "job_skills": [],
                    "salary": "",
                    "source": "JSearch",
                    "source_type": "web",
                    "publication_date": item.get("job_posted_at_datetime_utc", ""),
                })
                if len(jobs) >= limit:
                    break
    except Exception as e:
        logger.warning(f"JSearch API error: {e}")
    return jobs


def fetch_jobs(role: str = "", location: str = "Remote", source: str = "all") -> list[dict]:
    """
    Real-Time Job Search Engine Orchestrator.
    Fetches actual real-world job opportunities from live sources:
    Remotive, Arbeitnow, RemoteOK, Jobicy, plus Adzuna and JSearch (if configured).
    Every single job contains an authentic direct apply link to the original job listing.

    :param role: Target job role or search query (e.g. 'Frontend Developer', 'Python')
    :param location: Target location (e.g. 'Remote', 'Worldwide')
    :param source: 'all', 'remotive', 'arbeitnow', 'remoteok', 'jobicy', 'adzuna', or 'jsearch'
    :return: List of real-time verified job dictionaries
    """
    clean_role = (role or "Software Engineer").strip()
    clean_loc = (location or "Remote").strip()
    clean_source = (source or "all").lower().strip()

    cache_key = f"{clean_role}_{clean_loc}_{clean_source}".lower()

    # 1. In-memory cache check (15 minutes TTL)
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL and cached_data:
            return cached_data

    raw_jobs = []

    # 2. Check configured official APIs (Adzuna & JSearch)
    if clean_source in ["all", "adzuna"]:
        raw_jobs.extend(fetch_adzuna_jobs(clean_role, clean_loc, limit=15))

    if clean_source in ["all", "jsearch"]:
        raw_jobs.extend(fetch_jsearch_jobs(clean_role, clean_loc, limit=15))

    # 3. Query Real-Time Web Providers based on requested source
    if clean_source == "remotive":
        raw_jobs.extend(scrape_remotive(clean_role, limit=30))
    elif clean_source == "arbeitnow":
        raw_jobs.extend(scrape_arbeitnow(clean_role, limit=30))
    elif clean_source == "remoteok":
        raw_jobs.extend(scrape_remoteok(clean_role, limit=30))
    elif clean_source == "jobicy":
        raw_jobs.extend(scrape_jobicy(clean_role, limit=30))
    else:
        # Default / "all": Concurrently pull from Remotive, Arbeitnow, RemoteOK, and Jobicy
        scraped = scrape_live_jobs(role=clean_role, location=clean_loc, limit=40)
        raw_jobs.extend(scraped)

    # 4. Deduplicate and ensure all jobs have valid application links
    final_jobs = []
    seen = set()

    for job in raw_jobs:
        raw_url = job.get("job_apply_link", "").strip()
        title = job.get("job_title", "").strip()
        comp = (job.get("employer_name") or job.get("company", "")).strip()
        apply_url = normalize_apply_url(raw_url)

        # Reject jobs without a real apply link or empty title
        if not apply_url or not is_valid_apply_url(apply_url) or not title:
            continue

        job["job_apply_link"] = apply_url
        if not job.get("job_id"):
            job["job_id"] = generate_job_id(job)
        GLOBAL_JOBS_REGISTRY[job["job_id"]] = job

        key = (title.lower(), comp.lower())
        if key not in seen:
            seen.add(key)
            final_jobs.append(job)

    # 5. Cache and return
    if final_jobs:
        _CACHE[cache_key] = (final_jobs, time.time())

    return final_jobs
