import re
import urllib.parse
from bs4 import BeautifulSoup
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
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
    if not text:
        return ""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ufffd]", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def scrape_remoteok(role: str = "", limit: int = 15) -> list[dict]:
    """Scrape live jobs from RemoteOK API / RSS endpoints."""
    jobs = []
    try:
        tag = role.lower().strip()
        # Clean tag (e.g. 'Software Engineer (Android & Flutter)' -> 'android' or 'flutter')
        role_tokens = [t for t in re.findall(r"[a-zA-Z]+", tag) if len(t) > 2 and t not in ["software", "engineer", "developer", "senior", "junior", "lead"]]
        search_tag = role_tokens[0] if role_tokens else ""

        url = f"https://remoteok.com/api?tag={urllib.parse.quote(search_tag)}" if search_tag else "https://remoteok.com/api"
        response = requests.get(url, headers=HEADERS, timeout=6)
        if not response.ok:
            return jobs

        data = response.json()
        for item in data:
            if not isinstance(item, dict) or not item.get("position"):
                continue

            title = sanitize_text(item.get("position", ""))
            company = sanitize_text(item.get("company", "")) or "Tech Company"
            location = sanitize_text(item.get("location", "")) or "Remote"
            url_apply = item.get("url") or item.get("apply_url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
            description = sanitize_text(clean_html(item.get("description", "")))

            tags = [sanitize_text(t) for t in item.get("tags", []) if t]
            salary = sanitize_text(item.get("salary", ""))

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": "Full-time",
                "job_description": description[:1200] if description else f"{title} at {company}. Skills: {', '.join(tags)}",
                "job_apply_link": url_apply,
                "job_skills": tags,
                "salary": salary,
                "source": "Live Web (RemoteOK)",
                "source_type": "web",
            })
            if len(jobs) >= limit:
                break
    except Exception:
        pass
    return jobs


def scrape_remotive(role: str = "", limit: int = 15) -> list[dict]:
    """Scrape live jobs from Remotive API."""
    jobs = []
    try:
        search_query = role.strip()
        # Take key search term
        tokens = [t for t in re.findall(r"[a-zA-Z]+", search_query) if len(t) > 2 and t.lower() not in ["software", "engineer", "senior", "junior", "lead"]]
        query = tokens[0] if tokens else "developer"

        url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(query)}&limit={limit}"
        response = requests.get(url, headers=HEADERS, timeout=6)
        if not response.ok:
            return jobs

        data = response.json().get("jobs", [])
        for item in data:
            title = sanitize_text(item.get("title", ""))
            company = sanitize_text(item.get("company_name", "")) or "Hiring Company"
            location = sanitize_text(item.get("candidate_required_location", "")) or "Remote"
            url_apply = item.get("url") or f"https://www.google.com/search?q={urllib.parse.quote(title + ' ' + company)}"
            description = sanitize_text(clean_html(item.get("description", "")))
            tags = [sanitize_text(t) for t in item.get("tags", []) if t]
            salary = sanitize_text(item.get("salary", ""))
            emp_type = sanitize_text(item.get("job_type", "Full-time")).replace("_", " ").title()

            jobs.append({
                "job_title": title,
                "employer_name": company,
                "company": company,
                "job_city": location,
                "location": location,
                "job_employment_type": emp_type if emp_type else "Full-time",
                "job_description": description[:1200] if description else f"{title} at {company}. Skills: {', '.join(tags)}",
                "job_apply_link": url_apply,
                "job_skills": tags,
                "salary": salary,
                "source": "Live Web (Remotive)",
                "source_type": "web",
            })
            if len(jobs) >= limit:
                break
    except Exception:
        pass
    return jobs


def scrape_live_jobs(role: str = "", location: str = "Remote", limit: int = 25) -> list[dict]:
    """
    Combined multi-source live web scraper.
    Pulls real-time tech jobs from RemoteOK and Remotive.
    """
    all_scraped = []
    seen_titles = set()

    # 1. Scrape RemoteOK
    remoteok_jobs = scrape_remoteok(role=role, limit=limit // 2 + 5)
    for j in remoteok_jobs:
        key = (j["job_title"].lower().strip(), j["employer_name"].lower().strip())
        if key not in seen_titles:
            seen_titles.add(key)
            all_scraped.append(j)

    # 2. Scrape Remotive
    remotive_jobs = scrape_remotive(role=role, limit=limit // 2 + 5)
    for j in remotive_jobs:
        key = (j["job_title"].lower().strip(), j["employer_name"].lower().strip())
        if key not in seen_titles:
            seen_titles.add(key)
            all_scraped.append(j)

    return all_scraped[:limit]
