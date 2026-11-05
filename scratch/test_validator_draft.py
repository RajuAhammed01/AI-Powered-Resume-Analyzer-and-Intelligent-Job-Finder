import hashlib
import re
import urllib.parse

GLOBAL_JOBS_REGISTRY = {}

def normalize_apply_url(url: str, default_domain: str = "") -> str:
    """
    Ensure the application URL is absolute, clean, and properly formatted.
    Resolves relative paths using default_domain if needed.
    """
    if not url or not isinstance(url, str):
        return ""
    u = url.strip()
    if not u or u == "#" or u.lower().startswith("javascript:") or u.lower().startswith("mailto:"):
        return ""

    # If relative path starting with '/', resolve against default domain
    if u.startswith("/"):
        if default_domain:
            clean_domain = default_domain.rstrip("/")
            u = f"{clean_domain}{u}"
        else:
            return ""

    # If lacks scheme but has protocol-relative or www
    if not u.startswith("http://") and not u.startswith("https://"):
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("www."):
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
    Uses title, company, and apply_url to guarantee stability.
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


def find_job_by_identifier(user_id: int, identifier, user_cache: dict, db_lookup_fn=None) -> dict | None:
    """
    Find a job unambiguously by job_id string or positional integer index.
    Checks:
    1. User's active cached job list by matching job["job_id"] == str(identifier)
    2. Global registry of verified jobs by job_id == str(identifier)
    3. User's active cached job list by integer index 0 <= int(identifier) < len(list)
    4. Database lookup fallback via db_lookup_fn
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

    # 4. Database lookup fallback
    if db_lookup_fn:
        return db_lookup_fn(user_id, ident_str)

    return None

# Quick self-tests
assert is_valid_apply_url("https://remotive.com/jobs/react-dev") == True
assert is_valid_apply_url("http://example.com/apply") == True
assert is_valid_apply_url("/jobs/123") == False
assert normalize_apply_url("/jobs/123", "https://remoteok.com") == "https://remoteok.com/jobs/123"
assert is_valid_apply_url(normalize_apply_url("/jobs/123", "https://remoteok.com")) == True
assert is_valid_apply_url("#") == False
assert is_valid_apply_url("javascript:void(0)") == False
assert is_valid_apply_url("") == False

job1 = {"job_title": "Frontend Engineer", "company": "Vercel", "job_apply_link": "https://vercel.com/careers/fe"}
ensure_job_identity(job1)
assert len(job1["job_id"]) == 12
assert job1["job_id"] in GLOBAL_JOBS_REGISTRY

cache = {1: [job1]}
found_by_id = find_job_by_identifier(1, job1["job_id"], cache)
assert found_by_id is job1
found_by_idx = find_job_by_identifier(1, 0, cache)
assert found_by_idx is job1
found_by_idx_str = find_job_by_identifier(1, "0", cache)
assert found_by_idx_str is job1
assert find_job_by_identifier(1, "nonexistent", cache) is None

print("All draft validator tests PASSED!")

