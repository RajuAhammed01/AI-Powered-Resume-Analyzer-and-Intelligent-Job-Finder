import re

# Update job_scraper.py
scraper_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\job_scraper.py"
with open(scraper_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import if needed
if "from app.services.job_validator import" not in content:
    content = content.replace(
        "from app.services.profile_detector import UNRELATED_NON_TECH_KEYWORDS",
        "from app.services.profile_detector import UNRELATED_NON_TECH_KEYWORDS\nfrom app.services.job_validator import normalize_apply_url, generate_job_id, is_valid_apply_url"
    )

# Replace Remotive URL handling
old_remotive = """            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Hiring Company"
            raw_url = item.get("url", "").strip()
            if not raw_url or not title:
                continue"""

new_remotive = """            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://remotive.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue"""

content = content.replace(old_remotive, new_remotive)

# Replace Arbeitnow URL handling
old_arbeitnow = """            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Tech Employer"
            raw_url = item.get("url", "").strip()
            if not raw_url or not title:
                continue"""

new_arbeitnow = """            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Tech Employer"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://www.arbeitnow.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue"""

content = content.replace(old_arbeitnow, new_arbeitnow)

# Replace RemoteOK URL handling
old_remoteok = """            title = sanitize_text(item.get("position", ""))
            company = sanitize_text(item.get("company", "")) or "Hiring Company"
            raw_url = item.get("apply_url") or item.get("url") or ""
            if not raw_url or not title:
                continue"""

new_remoteok = """            title = sanitize_text(item.get("position", ""))
            company = sanitize_text(item.get("company", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("apply_url") or item.get("url") or "", default_domain="https://remoteok.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue"""

content = content.replace(old_remoteok, new_remoteok)

# Replace Jobicy URL handling
old_jobicy = """            title = sanitize_text(item.get("jobTitle", ""))
            company = sanitize_text(item.get("companyName", "")) or "Hiring Company"
            raw_url = item.get("url", "").strip()
            if not raw_url or not title:
                continue"""

new_jobicy = """            title = sanitize_text(item.get("jobTitle", ""))
            company = sanitize_text(item.get("companyName", "")) or "Hiring Company"
            raw_url = normalize_apply_url(item.get("url", "").strip(), default_domain="https://jobicy.com")
            if not raw_url or not title or not is_valid_apply_url(raw_url):
                continue"""

content = content.replace(old_jobicy, new_jobicy)

with open(scraper_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated job_scraper.py successfully.")


# Update job_api.py
api_path = r"e:\JobSnap\AI-Powered-Resume-Analyzer-and-Intelligent-Job-Finder\app\services\job_api.py"
with open(api_path, "r", encoding="utf-8") as f:
    api_content = f.read()

if "from app.services.job_validator import" not in api_content:
    api_content = api_content.replace(
        "from app.services.job_scraper import (",
        "from app.services.job_validator import (\n    normalize_apply_url,\n    is_valid_apply_url,\n    generate_job_id,\n    GLOBAL_JOBS_REGISTRY,\n)\nfrom app.services.job_scraper import ("
    )

old_dedup = """    for job in raw_jobs:
        apply_url = job.get("job_apply_link", "").strip()
        title = job.get("job_title", "").strip()
        comp = (job.get("employer_name") or job.get("company", "")).strip()

        # Reject jobs without a real apply link or empty title
        if not apply_url or apply_url == "#" or not title:
            continue

        key = (title.lower(), comp.lower())
        if key not in seen:
            seen.add(key)
            final_jobs.append(job)"""

new_dedup = """    for job in raw_jobs:
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
            final_jobs.append(job)"""

api_content = api_content.replace(old_dedup, new_dedup)

with open(api_path, "w", encoding="utf-8") as f:
    f.write(api_content)
print("Updated job_api.py successfully.")

