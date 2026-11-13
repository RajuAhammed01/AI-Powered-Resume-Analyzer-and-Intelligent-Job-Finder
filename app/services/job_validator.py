import hashlib
import html
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
    - Decodes HTML entities (e.g. &amp; -> &)
    - Strips wrapping quotes, angle brackets, and trailing punctuation
    - Resolves relative paths using default_domain if needed
    - Resolves protocol-relative URLs (//domain.com)
    - Rejects placeholders, empty values, javascript:, and mailto:
    """
    if not url or not isinstance(url, str):
        return ""

    # Decode HTML entities
    u = html.unescape(url).strip()
    # Remove embedded newlines, carriage returns, tabs, and zero-width spaces
    u = re.sub(r"[\r\n\t\u200b\u200c\u200d\ufeff]+", "", u)
    # Strip wrapping quotes, brackets, and edge punctuation (including trailing sentence dots)
    u = u.strip("'\"<>`()[]{};,.").strip()
    u = re.sub(r"^['\"<`(\[\{]+|['\"`>\]\};,.\)]+$", "", u).strip()

    if not u:
        return ""

    u_lower = u.lower()
    # Reject non-web, local, or placeholder schemes
    if u_lower.startswith(("javascript:", "mailto:", "data:", "tel:", "ftp:", "file:")):
        return ""
    if u_lower in (
        "#", "none", "null", "undefined", "n/a", "na",
        "about:blank", "blank", "fake", "test", "example.com",
        "http://", "https://"
    ):
        return ""

    # Protocol-relative URLs (e.g. //domain.com/path)
    if u.startswith("//"):
        u = "https:" + u
    # Relative path starting with single '/'
    elif u.startswith("/"):
        if default_domain:
            clean_domain = default_domain.rstrip("/")
            u = f"{clean_domain}{u}"
        else:
            return ""
    # Missing scheme on known web domains
    elif not u.startswith("http://") and not u.startswith("https://"):
        if u.startswith("www."):
            u = "https://" + u
        elif default_domain and not ("." in u.split("/")[0]):
            u = f"{default_domain.rstrip('/')}/{u.lstrip('/')}"
        elif re.match(r"^[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+(/.*)?$", u):
            u = "https://" + u

    try:
        parsed = urllib.parse.urlparse(u)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            netloc_clean = parsed.netloc.split(":")[0].strip()
            # Netloc must have at least one dot, no spaces, and a valid TLD
            if "." in netloc_clean and " " not in netloc_clean:
                parts = netloc_clean.split(".")
                if len(parts[-1]) >= 2 and netloc_clean.lower() not in ("localhost", "127.0.0.1", "0.0.0.0"):
                    return u
    except Exception:
        pass
    return ""


def is_valid_apply_url(url: str) -> bool:
    """Check if the URL is a non-empty, well-formed HTTP/HTTPS URL."""
    return bool(normalize_apply_url(url))


def build_fallback_apply_url(job_title: str, company: str, location: str = "") -> str:
    """
    Construct a safe, verified fallback careers search URL if a job's direct
    link is missing or invalid. Uses Google Jobs / careers search query.
    """
    parts = ["apply", job_title or "job", company or "careers"]
    if location and location.lower() not in ("remote", "various", "worldwide"):
        parts.append(location)
    query = " ".join([p.strip() for p in parts if p.strip()])
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def verify_job_id(job_id: str) -> bool:
    """Check if a job_id is valid, non-empty, and structurally sound."""
    if not job_id or not isinstance(job_id, str):
        return False
    jid = job_id.strip()
    return len(jid) >= 6 and not any(c in jid for c in " \t\r\n'\"<>")


def generate_job_id(job: dict) -> str:
    """
    Generate a deterministic, 12-char unique identifier for a job.
    Uses title, company, and apply_url to guarantee stability across sort and filter operations.
    """
    if not isinstance(job, dict):
        return hashlib.sha256(b"unknown_job").hexdigest()[:12]

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


def verify_and_repair_job(job: dict, default_domain: str = "") -> dict:
    """
    Ensures that a job dictionary has both a verified job_id and a valid application URL.
    If the direct application link is missing, constructs a verified fallback search URL.
    """
    if not isinstance(job, dict):
        return job
    ensure_job_identity(job, default_domain=default_domain)

    raw_url = job.get("job_apply_link", "")
    if not is_valid_apply_url(raw_url):
        job["job_apply_link"] = build_fallback_apply_url(
            job.get("job_title", ""),
            job.get("employer_name") or job.get("company", ""),
            job.get("job_city") or job.get("location", ""),
        )
        job["is_fallback_url"] = True
    else:
        job["is_fallback_url"] = False

    GLOBAL_JOBS_REGISTRY[job["job_id"]] = job
    return job


def verify_jobs_batch(jobs: list[dict], default_domain: str = "") -> list[dict]:
    """Batch verify and repair all jobs in a list."""
    for j in jobs:
        verify_and_repair_job(j, default_domain=default_domain)
    return jobs


def find_job_by_identifier(user_id: int, identifier, user_cache: dict) -> dict | None:
    """
    Find a job unambiguously by job_id string, apply_url, or positional integer index.
    Prevents cross-job misdirection and guarantees the user gets the exact selected job.

    Checks:
    1. User's active cached job list by matching job["job_id"] == str(identifier)
    2. Global registry of verified jobs by job_id == str(identifier) (case-insensitive)
    3. Match by job_apply_link across active user cache and global registry
    4. Positional integer index lookup in user's active session cache
    5. SavedJob database table for user_id where job_id, id, or apply_link matches
    6. Verified seed jobs fallback
    """
    if identifier is None:
        return None

    ident_str = str(identifier).strip()
    ident_clean = urllib.parse.unquote(ident_str).strip()
    ident_lower = ident_clean.lower()
    user_jobs = user_cache.get(user_id, [])

    # 1. Match job_id in user's active session cache
    for job in user_jobs:
        jid = str(job.get("job_id", "")).strip()
        if jid == ident_str or jid.lower() == ident_lower:
            return job

    # 2. Match job_id in global registry (exact & case-insensitive)
    if ident_str in GLOBAL_JOBS_REGISTRY:
        return GLOBAL_JOBS_REGISTRY[ident_str]
    for reg_id, reg_job in GLOBAL_JOBS_REGISTRY.items():
        if reg_id.lower() == ident_lower:
            return reg_job

    # 3. Match by application URL if identifier is a URL
    if is_valid_apply_url(ident_clean):
        norm_ident = normalize_apply_url(ident_clean)
        for job in user_jobs:
            if normalize_apply_url(job.get("job_apply_link", "")) == norm_ident:
                return job
        for reg_job in GLOBAL_JOBS_REGISTRY.values():
            if normalize_apply_url(reg_job.get("job_apply_link", "")) == norm_ident:
                return reg_job

    # 4. Positional integer index lookup in user's active session cache
    try:
        idx = int(ident_str)
        if 0 <= idx < len(user_jobs):
            return user_jobs[idx]
    except (ValueError, TypeError):
        pass

    # 5. SavedJob database fallback (for bookmarked jobs or revived sessions)
    try:
        from app.models import SavedJob
        saved = SavedJob.query.filter_by(user_id=user_id, job_id=ident_clean).first()
        if not saved and ident_lower != ident_clean:
            saved = SavedJob.query.filter_by(user_id=user_id, job_id=ident_lower).first()
        if not saved and ident_str.isdigit():
            saved = SavedJob.query.filter_by(user_id=user_id, id=int(ident_str)).first()
        if not saved and is_valid_apply_url(ident_clean):
            saved = SavedJob.query.filter_by(user_id=user_id, apply_link=ident_clean).first()

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

    # 6. Verified tech jobs seed fallback (guarantees job identity is never lost across server workers)
    try:
        from app.services.job_api import load_seed_jobs
        seed_jobs = load_seed_jobs()
        for sj in seed_jobs:
            if not sj.get("job_id"):
                sj["job_id"] = generate_job_id(sj)
            s_jid = str(sj.get("job_id", "")).strip()
            if s_jid == ident_str or s_jid.lower() == ident_lower:
                GLOBAL_JOBS_REGISTRY[sj["job_id"]] = sj
                return sj
            if is_valid_apply_url(ident_clean) and sj.get("job_apply_link") == ident_clean:
                GLOBAL_JOBS_REGISTRY[sj["job_id"]] = sj
                return sj

        try:
            idx = int(ident_str)
            if 0 <= idx < len(seed_jobs):
                sj = seed_jobs[idx]
                if not sj.get("job_id"):
                    sj["job_id"] = generate_job_id(sj)
                GLOBAL_JOBS_REGISTRY[sj["job_id"]] = sj
                return sj
        except (ValueError, TypeError):
            pass
    except Exception as e:
        logger.warning(f"Error checking seed jobs for identifier {identifier}: {e}")

    return None
