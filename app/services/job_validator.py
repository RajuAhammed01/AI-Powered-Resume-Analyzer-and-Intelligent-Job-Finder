import hashlib
import json
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)

# Global registry of active, verified job listings across user sessions
GLOBAL_JOBS_REGISTRY: dict[str, dict] = {}


def normalize_apply_url(url: str, default_domain: str = "") -> str:
    """
    Ensure the application URL is absolute, clean, and properly formatted.
    Resolves relative paths using default_domain if needed.
    Rejects placeholders, empty values, javascript:, and mailto:.
    """
    if not url or not isinstance(url, str):
        return ""
    u = url.strip()
    if not u or u == "#" or u.lower().startswith("javascript:") or u.lower().startswith("mailto:"):
        return ""

    # Protocol-relative URLs (e.g. //domain.com/path)
    if u.startswith("//"):
        u = "https:" + u
    # If relative path starting with single '/', resolve against default domain
    elif u.startswith("/"):
        if default_domain:
            clean_domain = default_domain.rstrip("/")
            u = f"{clean_domain}{u}"
        else:
            return ""
    # If lacks scheme but has www.
    elif not u.startswith("http://") and not u.startswith("https://"):
        if u.startswith("www."):
            u = "https://" + u

    try:
        parsed = urllib.parse.urlparse(u)
        if parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc:
            return u
    except Exception:
        pass
    return ""


def is_valid_apply_url(url: str) -> bool:
    """Check if the URL is a non-empty, well-formed HTTP/HTTPS URL."""
    return bool(normalize_apply_url(url))


def generate_job_id(job: dict) -> str:
    """
    Generate a deterministic, 12-char unique identifier for a job.
    Uses title, company, and apply_url to guarantee stability across sort and filter operations.
    """
    existing_id = job.get("job_id") or job.get("id")
    if existing_id and isinstance(existing_id, str) and len(existing_id) >= 6 and not existing_id.isdigit():
        return existing_id

    title = (job.get("job_title") or "").strip().lower()
    company = (job.get("employer_name") or job.get("company") or "").strip().lower()
    apply_url = (job.get("job_apply_link") or "").strip().lower()
    raw_key = f"{title}::{company}::{apply_url}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]


def ensure_job_identity(job: dict, default_domain: str = "") -> dict:
    """Populate job_id and normalize job_apply_link on a job dictionary."""
    if not isinstance(job, dict):
        return job
    raw_url = job.get("job_apply_link", "")
    norm_url = normalize_apply_url(raw_url, default_domain=default_domain)
    if norm_url:
        job["job_apply_link"] = norm_url
    if not job.get("job_id"):
        job["job_id"] = generate_job_id(job)
    GLOBAL_JOBS_REGISTRY[job["job_id"]] = job
    return job


def register_jobs(jobs: list[dict], default_domain: str = "") -> list[dict]:
    """Register and assign stable IDs to a list of jobs."""
    for j in jobs:
        ensure_job_identity(j, default_domain=default_domain)
    return jobs


def find_job_by_identifier(user_id: int, identifier, user_cache: dict) -> dict | None:
    """
    Find a job unambiguously by job_id string or positional integer index.
    Prevents cross-job misdirection and guarantees the user gets the exact selected job.

    Checks:
    1. User's active cached job list by matching job["job_id"] == str(identifier)
    2. Global registry of verified jobs by job_id == str(identifier)
    3. User's active cached job list by integer index 0 <= int(identifier) < len(list)
    4. SavedJob database table for user_id where job_id == str(identifier) or id == int(identifier)
    """
    if identifier is None:
        return None

    ident_str = str(identifier).strip()
    user_jobs = user_cache.get(user_id, [])

    # 1. Match job_id in user's active session cache
    for job in user_jobs:
        if str(job.get("job_id", "")).strip() == ident_str:
            return job

    # 2. Match job_id in global registry
    if ident_str in GLOBAL_JOBS_REGISTRY:
        return GLOBAL_JOBS_REGISTRY[ident_str]

    # 3. Positional integer index lookup in user's active session cache
    try:
        idx = int(ident_str)
        if 0 <= idx < len(user_jobs):
            return user_jobs[idx]
    except (ValueError, TypeError):
        pass

    # 4. SavedJob database fallback (for bookmarked jobs or revived sessions)
    try:
        from app.models import SavedJob
        saved = SavedJob.query.filter_by(user_id=user_id, job_id=ident_str).first()
        if not saved and ident_str.isdigit():
            saved = SavedJob.query.filter_by(user_id=user_id, id=int(ident_str)).first()
        if saved:
            matched_skills = []
            missing_skills = []
            try:
                matched_skills = json.loads(saved.matched_skills or "[]")
                missing_skills = json.loads(saved.missing_skills or "[]")
            except Exception:
                pass

            reconstructed_job = {
                "job_id": saved.job_id or ident_str,
                "job_title": saved.job_title,
                "employer_name": saved.company,
                "company": saved.company,
                "job_city": saved.location or "Remote",
                "location": saved.location or "Remote",
                "job_employment_type": saved.employment_type or "Full-time",
                "job_apply_link": saved.apply_link,
                "combined_score": saved.match_score or 85,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "source": "Saved Pipeline",
                "source_type": "database",
            }
            GLOBAL_JOBS_REGISTRY[reconstructed_job["job_id"]] = reconstructed_job
            return reconstructed_job
    except Exception as e:
        logger.warning(f"Error querying SavedJob fallback for identifier {identifier}: {e}")

    return None
