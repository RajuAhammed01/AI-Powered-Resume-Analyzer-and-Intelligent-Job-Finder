import json
import os
import pytest

from app.services.job_validator import (
    GLOBAL_JOBS_REGISTRY,
    build_fallback_apply_url,
    ensure_job_identity,
    find_job_by_identifier,
    generate_job_id,
    is_valid_apply_url,
    normalize_apply_url,
    verify_and_repair_job,
    verify_job_id,
    verify_jobs_batch,
)
from app.services.job_api import load_seed_jobs


def test_advanced_url_normalization_and_entity_decoding():
    """
    Verifies that application URLs with HTML entities, wrapping punctuation,
    or missing schemes are properly normalized into valid HTTP/HTTPS URLs.
    """
    # 1. HTML entities decoding (e.g. &amp; -> &)
    raw_entity_url = "https://lemon.io/for-developers/?utm_source=remotive&amp;utm_medium=job_ad&amp;utm_campaign=dev"
    norm = normalize_apply_url(raw_entity_url)
    assert "&amp;" not in norm
    assert "utm_source=remotive&utm_medium=job_ad" in norm
    assert is_valid_apply_url(norm)

    # 2. Wrapping quotes, angle brackets, and trailing punctuation
    assert normalize_apply_url("<https://jobs.lever.co/airbnb/101>") == "https://jobs.lever.co/airbnb/101"
    assert normalize_apply_url('"https://boards.greenhouse.io/stripe/jobs/202"') == "https://boards.greenhouse.io/stripe/jobs/202"
    assert normalize_apply_url("https://company.com/careers/role.") == "https://company.com/careers/role"
    assert normalize_apply_url("https://company.com/careers/role,") == "https://company.com/careers/role"

    # 3. Missing scheme on valid domain
    assert normalize_apply_url("boards.greenhouse.io/stripe/jobs/303") == "https://boards.greenhouse.io/stripe/jobs/303"
    assert normalize_apply_url("www.arbeitnow.com/view/developer-1") == "https://www.arbeitnow.com/view/developer-1"

    # 4. Relative paths with default domain
    assert normalize_apply_url("/jobs/detail/404", default_domain="https://remotive.com") == "https://remotive.com/jobs/detail/404"
    assert normalize_apply_url("view/dev-505", default_domain="https://arbeitnow.com") == "https://arbeitnow.com/view/dev-505"

    # 5. Invalid / placeholder rejection
    invalid_cases = [
        "",
        " ",
        "#",
        "None",
        "null",
        "undefined",
        "N/A",
        "about:blank",
        "javascript:void(0)",
        "mailto:careers@company.com",
        "tel:+1234567890",
        "file:///C:/path/to/job",
        "localhost:5000/job",
        "fake",
        "http://",
        "https://",
    ]
    for inv in invalid_cases:
        assert normalize_apply_url(inv) == "", f"Expected empty string for invalid URL: {inv}"
        assert not is_valid_apply_url(inv), f"Expected False for invalid URL: {inv}"


def test_verify_job_id():
    """
    Verifies that job IDs are validated for minimum length, presence, and no illegal characters.
    """
    assert verify_job_id("1b8db5025c0e") is True
    assert verify_job_id("job_react_101") is True
    assert verify_job_id("senior-dev-999") is True

    assert verify_job_id("") is False
    assert verify_job_id(None) is False
    assert verify_job_id("123") is False  # too short
    assert verify_job_id("job id with spaces") is False
    assert verify_job_id("job\nid\nnewlines") is False
    assert verify_job_id("<job_id>") is False


def test_build_fallback_apply_url():
    """
    Verifies that when a direct application link is missing, a valid fallback search URL is constructed.
    """
    fallback = build_fallback_apply_url("Senior Python Developer", "Microsoft", "Remote")
    assert is_valid_apply_url(fallback)
    assert fallback.startswith("https://www.google.com/search?q=")
    assert "Python" in fallback or "python" in fallback


def test_verify_and_repair_job():
    """
    Tests that jobs with missing IDs or broken links are automatically verified and repaired.
    """
    broken_job = {
        "job_title": "Lead Cloud Architect",
        "company": "Amazon Web Services",
        "employer_name": "Amazon Web Services",
        "job_city": "Seattle, WA",
        "job_apply_link": "javascript:void(0)",  # Invalid
    }

    repaired = verify_and_repair_job(broken_job)
    assert verify_job_id(repaired["job_id"]) is True
    assert is_valid_apply_url(repaired["job_apply_link"]) is True
    assert repaired["is_fallback_url"] is True
    assert repaired["job_id"] in GLOBAL_JOBS_REGISTRY


def test_find_job_by_identifier_case_insensitive_and_url():
    """
    Verifies that find_job_by_identifier successfully resolves jobs case-insensitively
    and by application URL.
    """
    test_job = {
        "job_id": "a1b2c3d4e5f6",
        "job_title": "DevOps Engineer",
        "company": "CloudScale",
        "employer_name": "CloudScale",
        "job_apply_link": "https://cloudscale.io/careers/devops",
    }
    ensure_job_identity(test_job)
    user_cache = {101: [test_job]}

    # 1. Exact job_id
    assert find_job_by_identifier(101, "a1b2c3d4e5f6", user_cache) is not None

    # 2. Uppercase job_id (case-insensitive)
    assert find_job_by_identifier(101, "A1B2C3D4E5F6", user_cache) is not None

    # 3. By application URL
    assert find_job_by_identifier(101, "https://cloudscale.io/careers/devops", user_cache) is not None


def test_all_seed_jobs_have_verified_ids_and_urls():
    """
    Verifies that all 113 pre-verified seed jobs in data/verified_jobs_seed.json
    have valid, non-empty, unique job IDs and valid HTTP/HTTPS application URLs.
    """
    seed_jobs = load_seed_jobs()
    assert len(seed_jobs) >= 100, f"Expected at least 100 seed jobs, got {len(seed_jobs)}"

    all_ids = []
    all_urls = []

    for job in seed_jobs:
        # 1. Verify job ID
        jid = job.get("job_id")
        assert jid is not None and len(jid) >= 6, f"Job missing valid job_id: {job.get('job_title')}"
        assert verify_job_id(jid) is True, f"Job ID invalid: {jid}"
        all_ids.append(jid)

        # 2. Verify application URL
        url = job.get("job_apply_link")
        assert is_valid_apply_url(url), f"Job has invalid apply URL: {url} ({job.get('job_title')})"
        assert url.startswith("http://") or url.startswith("https://")
        all_urls.append(url)

    # 3. Verify zero ID collisions
    assert len(all_ids) == len(set(all_ids)), f"Duplicate job IDs detected: {len(all_ids) - len(set(all_ids))} duplicates"
    # 4. Verify zero URL collisions
    assert len(all_urls) == len(set(all_urls)), f"Duplicate apply URLs detected: {len(all_urls) - len(set(all_urls))} duplicates"

