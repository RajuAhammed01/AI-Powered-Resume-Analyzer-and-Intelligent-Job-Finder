import os
import requests
import time

_CACHE = {}
CACHE_TTL = 3600  # 1 hour

STATIC_JOBS = [
    {
        "job_title": "Python Developer",
        "employer_name": "Tech Corp",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_description": "We are looking for a Python Developer with experience in Django, SQL, and APIs. Must know Git.",
        "job_apply_link": "#"
    },
    {
        "job_title": "Data Analyst",
        "employer_name": "DataWorks",
        "job_city": "New York",
        "job_employment_type": "Contract",
        "job_description": "Seeking a Data Analyst proficient in Pandas, SQL, Excel, and Power BI.",
        "job_apply_link": "#"
    },
    {
        "job_title": "Frontend Engineer",
        "employer_name": "Web Solutions",
        "job_city": "San Francisco",
        "job_employment_type": "Full-time",
        "job_description": "Experience required with React, JavaScript, HTML, CSS, and Figma.",
        "job_apply_link": "#"
    }
]

def fetch_jobs(role, location):
    cache_key = f"{role}_{location}".lower()
    
    # Check cache
    if cache_key in _CACHE:
        cached_data, timestamp = _CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data

    api_key = os.getenv("JSEARCH_API_KEY")
    if not api_key or api_key == "your_key_here":
        return STATIC_JOBS

    try:
        response = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={"query": f"{role} in {location}", "page": "1", "num_pages": "1"},
            timeout=15,
        )
        if response.ok:
            data = response.json().get("data", [])
            _CACHE[cache_key] = (data, time.time())
            return data
    except Exception as e:
        pass
        
    return STATIC_JOBS
