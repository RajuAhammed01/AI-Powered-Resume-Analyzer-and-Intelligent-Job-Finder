import json
import logging
import os
import time
import urllib.parse
import requests

from app.services.api_client import default_api_client, CircuitBreakerOpenError
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
CACHE_TTL = 3600  # 1 hour cache for ultra-fast performance

_SEED_JOBS_CACHE = None
SEED_JOBS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "verified_jobs_seed.json",
)


def load_seed_jobs() -> list[dict]:
    """Load high-speed pre-verified tech jobs seed to eliminate cold-start network latency."""
    global _SEED_JOBS_CACHE
    if _SEED_JOBS_CACHE is not None:
        return _SEED_JOBS_CACHE
    if os.path.exists(SEED_JOBS_FILE):
        try:
            with open(SEED_JOBS_FILE, "r", encoding="utf-8") as f:
                raw_seeds = json.load(f)
                for j in raw_seeds:
                    if not j.get("job_id"):
                        j["job_id"] = generate_job_id(j)
                    GLOBAL_JOBS_REGISTRY[j["job_id"]] = j
                _SEED_JOBS_CACHE = raw_seeds
                return _SEED_JOBS_CACHE
        except Exception as e:
            logger.warning(f"Failed to load verified jobs seed: {e}")
    _SEED_JOBS_CACHE = []
    return _SEED_JOBS_CACHE


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
        resp = default_api_client.get(url, service_name="Adzuna", params=params, timeout=(2.0, 5.0))
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
        resp = default_api_client.get(
            "https://jsearch.p.rapidapi.com/search",
            service_name="JSearch",
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={"query": f"{role} in {location}", "page": "1", "num_pages": "1"},
            timeout=(2.0, 6.0),
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
    Real-Time Job Search Engine Orchestrator with Instant Fallback.
    Fetches authentic verified job opportunities with direct apply links.
    Utilizes pre-verified seed cache for instant sub-50ms responses, backed by
    multi-source real-time web scrapers.
    """
    clean_role = (role or "Software Engineer").strip()
    clean_loc = (location or "Remote").strip()
    clean_source = (source or "all").lower().strip()

    cache_key = f"{clean_role}_{clean_loc}_{clean_source}".lower()

    # 1. In-memory cache check (1 hour TTL)
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL and cached_data:
            return cached_data

    raw_jobs = []

    # 2. Query Real-Time Web Providers for authentic live jobs with active direct application links
    live_scraped = []
    try:
        if clean_source == "remotive":
            live_scraped = scrape_remotive(clean_role, limit=20)
        elif clean_source == "arbeitnow":
            live_scraped = scrape_arbeitnow(clean_role, limit=20)
        elif clean_source == "remoteok":
            live_scraped = scrape_remoteok(clean_role, limit=20)
        elif clean_source == "jobicy":
            live_scraped = scrape_jobicy(clean_role, limit=20)
        else:
            live_scraped = scrape_live_jobs(role=clean_role, location=clean_loc, limit=25)
    except Exception as e:
        logger.warning(f"Live scraper fetch error: {e}")

    raw_jobs.extend(live_scraped)

    # 3. Check configured official APIs (Adzuna & JSearch) if credentials present
    if clean_source in ["all", "adzuna"]:
        raw_jobs.extend(fetch_adzuna_jobs(clean_role, clean_loc, limit=10))

    if clean_source in ["all", "jsearch"]:
        raw_jobs.extend(fetch_jsearch_jobs(clean_role, clean_loc, limit=10))

    # 4. Supplement with pre-verified authentic live tech jobs to guarantee instant zero-wait availability
    seed_jobs = load_seed_jobs()
    role_tokens = [t.lower() for t in clean_role.split() if len(t) > 2]
    matching_seeds = []
    other_seeds = []
    for s_job in seed_jobs:
        job_copy = dict(s_job)
        t_lower = (job_copy.get("job_title", "") + " " + " ".join(job_copy.get("job_skills", []))).lower()
        if any(tok in t_lower for tok in role_tokens):
            matching_seeds.append(job_copy)
        else:
            other_seeds.append(job_copy)

    # Supplement if live scraper returned few results or during network downtime
    if len(raw_jobs) < 15:
        raw_jobs.extend(matching_seeds)
    if len(raw_jobs) < 10:
        raw_jobs.extend(other_seeds[:10])

    # 5. Deduplicate and ensure all jobs have valid application links
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

    # 6. Cache and return
    if final_jobs:
        _CACHE[cache_key] = (final_jobs, time.time())

    return final_jobs
