import logging
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests

from app.services.profile_detector import UNRELATED_NON_TECH_KEYWORDS
from app.services.job_validator import normalize_apply_url, generate_job_id, is_valid_apply_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
}

GENERIC_ROLE_NOUNS = {
    "developer", "engineer", "programmer", "architect", "specialist",
    "consultant", "lead", "senior", "junior", "intern", "staff", "manager",
    "director", "head", "associate", "expert", "officer",
}


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and condense whitespace, keeping text clean."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw_html)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sanitize_text(text: str) -> str:
    """Remove control characters and condense whitespace."""
    if not text:
        return ""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufffd]", " ", str(text))
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def is_unrelated_non_tech(title: str, description: str = "") -> bool:
    """Return True if job title explicitly indicates an unrelated non-tech field."""
    t = (title or "").lower()
    for kw in UNRELATED_NON_TECH_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return True
    return False


def extract_keywords(role: str) -> tuple[list[str], list[str]]:
    """
    Extract search tokens from a role string.
    Returns:
        (all_tokens, discriminating_tokens)
    """
    stop_words = {"a", "an", "the", "and", "or", "in", "for", "with", "at", "to"}
    raw_tokens = [
        t.lower() for t in re.findall(r"[a-zA-Z0-9#\+]+", role or "")
        if len(t) > 1 and t.lower() not in stop_words
    ]
    discriminating = [t for t in raw_tokens if t not in GENERIC_ROLE_NOUNS]
    return raw_tokens, discriminating


def _build_remotive_search_param(role: str) -> str:
    """Construct a clean, high-yield search term for Remotive API."""
    r_lower = (role or "").lower().strip()
    if "frontend" in r_lower or "front-end" in r_lower:
        return "frontend"
    if "react" in r_lower:
        return "react"
    if "machine learning" in r_lower or "deep learning" in r_lower:
        return "machine learning"
    if "data analyst" in r_lower or "data science" in r_lower or "data scientist" in r_lower:
        return "data"
    if "ai engineer" in r_lower or "artificial intelligence" in r_lower:
        return "ai"
    if "python" in r_lower:
        return "python"
    if "devops" in r_lower or "cloud" in r_lower:
        return "devops"
    if "mobile" in r_lower or "android" in r_lower or "ios" in r_lower:
        return "mobile"
    if "full stack" in r_lower or "fullstack" in r_lower:
        return "fullstack"
    if "backend" in r_lower or "back-end" in r_lower:
        return "backend"

    all_tokens, discriminating = extract_keywords(role)
    return discriminating[0] if discriminating else (all_tokens[0] if all_tokens else "developer")


def _is_job_relevant_to_role(title: str, tags: list[str], desc: str, discriminating_tokens: list[str], role: str) -> bool:
    """Check if job matches the candidate's target role or discriminating tokens, enforcing strict domain category gates."""
    if is_unrelated_non_tech(title, desc):
        return False

    from app.services.profile_detector import classify_job_domain, is_job_domain_compatible
    job_domain_info = classify_job_domain(title, desc, tags)
    job_dom = job_domain_info["domain"]
    role_dom = classify_job_domain(role)["domain"]

    # Reject if the job's career category is incompatible with the target role
    is_compat, _, _ = is_job_domain_compatible(role_dom, job_dom)
    if not is_compat:
        return False

    t_lower = title.lower()

    # Specific category guards:
    if role_dom == "frontend":
        # Discard network/systems or writing roles
        if any(un in t_lower for un in ["network", "writer", "copywriter", "sysadmin", "system administrator", "it support"]):
            return False
        # Must possess at least one frontend indicator in title or tags
        frontend_markers = ["frontend", "front-end", "react", "vue", "angular", "ui", "web", "javascript", "typescript", "client-side"]
        has_marker = any(m in t_lower for m in frontend_markers) or any(any(m in tag.lower() for m in frontend_markers) for tag in tags)
        if not has_marker:
            return False

    elif role_dom == "data_ml":
        if any(un in t_lower for un in ["writer", "copywriter", "frontend", "front-end", "network", "it support"]):
            return False
        data_markers = ["data", "machine learning", "ml", "ai", "deep learning", "nlp", "computer vision", "analytics", "statistic", "python"]
        has_marker = any(m in t_lower for m in data_markers) or any(any(m in tag.lower() for m in data_markers) for tag in tags)
        if not has_marker:
            return False

    if not discriminating_tokens:
        return True

    text_to_check = f"{title} {' '.join(tags)} {desc[:300]}".lower()

    # Exact multi-word match (e.g. "machine learning", "data analyst", "react developer")
    r_clean = role.lower().strip()
    if len(r_clean) > 4 and r_clean in text_to_check:
        return True

    # Discriminating keyword check (e.g. "react", "frontend", "python", "data")
    match_count = sum(1 for dt in discriminating_tokens if dt in text_to_check)
    return match_count >= 1


def scrape_remotive(role: str = "", limit: int = 25) -> list[dict]:
    """
    Fetch real-time live tech jobs from Remotive API.
    Provides direct application links to authentic company postings.
    """
    jobs = []
    try:
        search_param = _build_remotive_search_param(role)
        url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(search_param)}&limit={max(30, limit)}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if not response.ok:
            return jobs

        data = response.json().get("jobs", [])
        all_tokens, discriminating = extract_keywords(role)

        for item in data:
            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://remotive.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue

            location = sanitize_text(item.get("candidate_required_location", "")) or "Remote"
            description = sanitize_text(clean_html(item.get("description", "")))
            tags = [sanitize_text(t) for t in item.get("tags", []) if t]

            # Domain and relevance filtering
            if not _is_job_relevant_to_role(title, tags, description, discriminating, role):
                continue

            salary = sanitize_text(item.get("salary", ""))
            job_type = sanitize_text(item.get("job_type", "Full-time")).replace("_", " ").title()

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": job_type if job_type else "Full-time",
                "job_description": description[:1400] if description else f"{title} at {company}. Skills: {', '.join(tags)}",
                "job_apply_link": raw_url,
                "job_skills": tags,
                "salary": salary,
                "source": "Remotive",
                "source_type": "web",
                "publication_date": item.get("publication_date", ""),
            })
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.warning(f"Error fetching from Remotive: {e}")
    return jobs


def scrape_arbeitnow(role: str = "", limit: int = 25) -> list[dict]:
    """
    Fetch real-time jobs from Arbeitnow Job Board API.
    Features active remote and global tech opportunities with direct employer apply URLs.
    """
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if not response.ok:
            return jobs

        data = response.json().get("data", [])
        all_tokens, discriminating = extract_keywords(role)

        for item in data:
            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Tech Employer"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://www.arbeitnow.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue

            tags = [sanitize_text(t) for t in item.get("tags", []) if t]
            desc = sanitize_text(clean_html(item.get("description", "")))

            # Strict relevance filter against discriminating domain tokens
            if not _is_job_relevant_to_role(title, tags, desc, discriminating, role):
                continue

            is_remote = item.get("remote", False)
            raw_loc = sanitize_text(item.get("location", ""))
            location = raw_loc if raw_loc else ("Remote" if is_remote else "Global")

            job_types = item.get("job_types", ["Full-time"])
            emp_type = job_types[0] if job_types else "Full-time"

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": emp_type,
                "job_description": desc[:1400] if desc else f"{title} at {company}.",
                "job_apply_link": raw_url,
                "job_skills": tags,
                "salary": "",
                "source": "Arbeitnow",
                "source_type": "web",
                "publication_date": item.get("created_at", ""),
            })
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.warning(f"Error fetching from Arbeitnow: {e}")
    return jobs


def scrape_remoteok(role: str = "", limit: int = 25) -> list[dict]:
    """
    Fetch real-time jobs from RemoteOK API.
    Provides direct application links to live remote tech roles.
    """
    jobs = []
    try:
        url = "https://remoteok.com/api"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if not response.ok:
            return jobs

        data = response.json()
        all_tokens, discriminating = extract_keywords(role)

        for item in data:
            if not isinstance(item, dict) or not item.get("position"):
                continue

            title = sanitize_text(item.get("position", ""))
            company = sanitize_text(item.get("company", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("apply_url") or item.get("url") or "", default_domain="https://remoteok.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue

            tags = [sanitize_text(t) for t in item.get("tags", []) if t]
            desc = sanitize_text(clean_html(item.get("description", "")))

            if not _is_job_relevant_to_role(title, tags, desc, discriminating, role):
                continue

            location = sanitize_text(item.get("location", "")) or "Remote"
            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            salary = f"${salary_min:,} - ${salary_max:,}" if salary_min and salary_max else sanitize_text(item.get("salary", ""))

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": "Full-time",
                "job_description": desc[:1400] if desc else f"{title} at {company}. Skills: {', '.join(tags)}",
                "job_apply_link": raw_url,
                "job_skills": tags,
                "salary": salary,
                "source": "RemoteOK",
                "source_type": "web",
                "publication_date": str(item.get("date", "")),
            })
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.warning(f"Error fetching from RemoteOK: {e}")
    return jobs


def scrape_jobicy(role: str = "", limit: int = 20) -> list[dict]:
    """
    Fetch real-time remote jobs from Jobicy API.
    Provides live remote jobs with direct application URLs.
    """
    jobs = []
    try:
        r_lower = (role or "").lower()
        tag = ""
        if "intern" in r_lower:
            tag = "internship"
        elif "react" in r_lower:
            tag = "react"
        elif "frontend" in r_lower or "front-end" in r_lower:
            tag = "frontend"
        elif "data" in r_lower or "machine" in r_lower or "ai" in r_lower:
            tag = "data"
        elif "python" in r_lower:
            tag = "python"
        elif "devops" in r_lower:
            tag = "devops"
        else:
            _, discriminating = extract_keywords(role)
            tag = discriminating[0] if discriminating else "dev"

        url = f"https://jobicy.com/api/v2/remote-jobs?count={limit}&tag={urllib.parse.quote(tag)}" if tag else f"https://jobicy.com/api/v2/remote-jobs?count={limit}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        if not response.ok:
            return jobs

        data = response.json().get("jobs", [])
        all_tokens, discriminating = extract_keywords(role)

        for item in data:
            title = sanitize_text(item.get("jobTitle", ""))
            company = sanitize_text(item.get("companyName", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://jobicy.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue

            desc = sanitize_text(clean_html(item.get("jobDescription", "") or item.get("jobExcerpt", "")))
            skills = [sanitize_text(item.get("jobIndustry", ""))] if item.get("jobIndustry") else []

            if not _is_job_relevant_to_role(title, skills, desc, discriminating, role):
                continue

            location = sanitize_text(item.get("jobGeo", "")) or "Remote"
            raw_types = item.get("jobType", ["Full-time"])
            emp_type = raw_types[0] if isinstance(raw_types, list) and raw_types else "Full-time"

            salary_min = item.get("salaryMin")
            salary_max = item.get("salaryMax")
            currency = item.get("salaryCurrency", "USD")
            salary = f"{currency} {salary_min:,} - {salary_max:,}" if salary_min and salary_max else ""

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": emp_type,
                "job_description": desc[:1400] if desc else f"{title} at {company}.",
                "job_apply_link": raw_url,
                "job_skills": skills,
                "salary": salary,
                "source": "Jobicy",
                "source_type": "web",
                "publication_date": item.get("pubDate", ""),
            })
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.warning(f"Error fetching from Jobicy: {e}")
    return jobs


def scrape_live_jobs(role: str = "", location: str = "Remote", limit: int = 35) -> list[dict]:
    """
    Combined multi-source real-time job search orchestrator.
    Queries Remotive, Arbeitnow, RemoteOK, and Jobicy concurrently in parallel threads.
    Every returned job has a verified, direct external application URL and is filtered
    to match the candidate's target career domain.
    """
    clean_role = (role or "Software Engineer").strip()
    per_source_limit = max(12, limit // 2)

    all_jobs = []
    seen_keys = set()

    # Query all 4 sources simultaneously for sub-2-second speed
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(scrape_remotive, clean_role, per_source_limit): "Remotive",
            executor.submit(scrape_arbeitnow, clean_role, per_source_limit): "Arbeitnow",
            executor.submit(scrape_remoteok, clean_role, per_source_limit): "RemoteOK",
            executor.submit(scrape_jobicy, clean_role, per_source_limit): "Jobicy",
        }

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                results = future.result()
                for job in results:
                    key = (job["job_title"].lower().strip(), (job["employer_name"] or job["company"]).lower().strip())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_jobs.append(job)
            except Exception as e:
                logger.warning(f"Provider {source_name} failed: {e}")

    # Fallback only if very few jobs returned, but keep fallback strictly technical
    if len(all_jobs) < 5:
        _, discriminating = extract_keywords(clean_role)
        fallback_query = discriminating[0] if discriminating else "developer"
        fallback_remotive = scrape_remotive(fallback_query, limit=10)
        for job in fallback_remotive:
            key = (job["job_title"].lower().strip(), (job["employer_name"] or job["company"]).lower().strip())
            if key not in seen_keys:
                seen_keys.add(key)
                all_jobs.append(job)

    return all_jobs[:limit]
