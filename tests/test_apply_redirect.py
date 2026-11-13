import json
from unittest.mock import patch
import pytest

from app import create_app
from app.extensions import db
from app.models import JobPreference, Resume, SavedJob, User
from app.routes.jobs import USER_JOBS_CACHE
from app.services.job_validator import (
    GLOBAL_JOBS_REGISTRY,
    ensure_job_identity,
    find_job_by_identifier,
    generate_job_id,
    is_valid_apply_url,
    normalize_apply_url,
)


@pytest.fixture
def app():
    app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_user(app, client):
    user = User(name="Alex Rivers", email="alex@example.com", title_role="Frontend Developer")
    user.set_password("SecurePass123!")
    db.session.add(user)
    db.session.commit()

    resume = Resume(
        user_id=user.id,
        filename="alex_frontend.pdf",
        extracted_skills=json.dumps(["React", "JavaScript", "TypeScript", "HTML5", "CSS3"]),
        extracted_text="Alex Rivers. Frontend Developer specializing in React and TypeScript.",
    )
    pref = JobPreference(
        user_id=user.id,
        target_role="Frontend Developer",
        location="Remote",
    )
    db.session.add(resume)
    db.session.add(pref)
    db.session.commit()

    # Log in
    client.post("/login", data={"email": "alex@example.com", "password": "SecurePass123!"})
    return user


def test_url_normalization_and_validation():
    # Valid absolute HTTP/HTTPS URLs
    assert is_valid_apply_url("https://remotive.com/jobs/react-engineer-101")
    assert is_valid_apply_url("http://boards.greenhouse.io/stripe/jobs/12345")
    assert is_valid_apply_url("https://jobs.lever.co/airbnb/98765")

    # Relative URLs resolved with default domain
    norm = normalize_apply_url("/remote-jobs/12345", default_domain="https://remoteok.com")
    assert norm == "https://remoteok.com/remote-jobs/12345"
    assert is_valid_apply_url(norm)

    # Protocol-relative URLs
    norm2 = normalize_apply_url("//arbeitnow.com/view/fe-dev", default_domain="")
    assert norm2 == "https://arbeitnow.com/view/fe-dev"
    assert is_valid_apply_url(norm2)

    # Invalid / empty / placeholder URLs
    assert not is_valid_apply_url("")
    assert not is_valid_apply_url("#")
    assert not is_valid_apply_url("javascript:void(0)")
    assert not is_valid_apply_url("mailto:jobs@example.com")
    assert not is_valid_apply_url(None)
    assert not is_valid_apply_url("invalid-url-string")


def test_generate_job_id_deterministic():
    job_a1 = {
        "job_title": "React Developer",
        "company": "Tech Corp",
        "job_apply_link": "https://techcorp.com/careers/react-1",
    }
    job_a2 = {
        "job_title": "React Developer",
        "company": "Tech Corp",
        "job_apply_link": "https://techcorp.com/careers/react-1",
    }
    job_b = {
        "job_title": "Frontend Engineer",
        "company": "Startup Co",
        "job_apply_link": "https://startup.io/jobs/fe",
    }

    id_a1 = generate_job_id(job_a1)
    id_a2 = generate_job_id(job_a2)
    id_b = generate_job_id(job_b)

    assert id_a1 == id_a2, "generate_job_id must be deterministic"
    assert id_a1 != id_b, "different jobs must have different job_ids"
    assert len(id_a1) == 12


def test_apply_redirect_to_exact_selected_job(client, auth_user):
    job_0 = {
        "job_title": "Senior React Engineer",
        "employer_name": "Vercel",
        "company": "Vercel",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_apply_link": "https://vercel.com/careers/senior-react-engineer",
        "combined_score": 92,
        "job_skills": ["React", "TypeScript", "Next.js"],
        "matched_skills": ["React", "TypeScript"],
        "missing_skills": ["Next.js"],
    }
    job_1 = {
        "job_title": "Frontend UI Developer",
        "employer_name": "Shopify",
        "company": "Shopify",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_apply_link": "https://shopify.com/careers/frontend-ui",
        "combined_score": 86,
        "job_skills": ["JavaScript", "HTML5", "CSS3"],
        "matched_skills": ["JavaScript", "HTML5", "CSS3"],
        "missing_skills": [],
    }

    ensure_job_identity(job_0)
    ensure_job_identity(job_1)
    job_0["cache_id"] = 0
    job_1["cache_id"] = 1

    USER_JOBS_CACHE[auth_user.id] = [job_0, job_1]

    # 1. Apply to job_0 by job_id
    resp_0_id = client.get(f"/job/apply/{job_0['job_id']}")
    assert resp_0_id.status_code == 302
    assert resp_0_id.location == "https://vercel.com/careers/senior-react-engineer"

    # 2. Apply to job_0 by index 0
    resp_0_idx = client.get("/job/apply/0")
    assert resp_0_idx.status_code == 302
    assert resp_0_idx.location == "https://vercel.com/careers/senior-react-engineer"

    # 3. Apply to job_1 by job_id
    resp_1_id = client.get(f"/job/apply/{job_1['job_id']}")
    assert resp_1_id.status_code == 302
    assert resp_1_id.location == "https://shopify.com/careers/frontend-ui"

    # 4. Apply to job_1 by index 1
    resp_1_idx = client.get("/job/apply/1")
    assert resp_1_idx.status_code == 302
    assert resp_1_idx.location == "https://shopify.com/careers/frontend-ui"

    # Verify both applications tracked in SavedJob
    saved_vercel = SavedJob.query.filter_by(user_id=auth_user.id, company="Vercel").first()
    assert saved_vercel is not None
    assert saved_vercel.status == "Applied"
    assert saved_vercel.apply_link == "https://vercel.com/careers/senior-react-engineer"

    saved_shopify = SavedJob.query.filter_by(user_id=auth_user.id, company="Shopify").first()
    assert saved_shopify is not None
    assert saved_shopify.status == "Applied"
    assert saved_shopify.apply_link == "https://shopify.com/careers/frontend-ui"


def test_apply_redirect_handles_invalid_url_without_misdirection(client, auth_user):
    broken_job = {
        "job_title": "Mystery Frontend Role",
        "employer_name": "Ghost Inc",
        "company": "Ghost Inc",
        "job_city": "Remote",
        "job_employment_type": "Full-time",
        "job_apply_link": "#",  # Invalid link
        "combined_score": 75,
        "job_skills": ["React"],
    }
    ensure_job_identity(broken_job)
    broken_job["cache_id"] = 0
    USER_JOBS_CACHE[auth_user.id] = [broken_job]

    # When user attempts to apply, system must NOT redirect externally to another site
    resp = client.get(f"/job/apply/{broken_job['job_id']}", follow_redirects=False)
    assert resp.status_code == 302
    # Redirects safely to the internal job details page instead of an external website
    assert f"/job/{broken_job['job_id']}" in resp.location


def test_apply_redirect_unknown_job_id_safely_handled(client, auth_user):
    USER_JOBS_CACHE[auth_user.id] = []
    resp = client.get("/job/apply/completely_nonexistent_job_12345", follow_redirects=False)
    assert resp.status_code == 302
    assert "/results" in resp.location


def test_quick_apply_form_records_and_redirects_accurately(client, auth_user):
    form_data = {
        "job_id": "job_custom_99",
        "job_title": "React Native Specialist",
        "company": "Mobile Pioneers",
        "apply_link": "https://mobilepioneers.com/careers/rn-spec",
        "location": "Remote",
        "match_score": "88",
    }
    resp = client.post("/apply-job", data=form_data, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.location == "https://mobilepioneers.com/careers/rn-spec"

    # Verify database record
    saved = SavedJob.query.filter_by(user_id=auth_user.id, company="Mobile Pioneers").first()
    assert saved is not None
    assert saved.status == "Applied"
    assert saved.apply_link == "https://mobilepioneers.com/careers/rn-spec"
    assert saved.match_score == 88


def test_sorting_preserves_exact_apply_target(client, auth_user):
    """
    Simulate the exact scenario where jobs are sorted by seniority or match score.
    Verify that even when list order changes, each job's apply link remains 100% accurate.
    """
    job_experienced = {
        "job_title": "Staff React Architect",
        "company": "Big Tech Corp",
        "employer_name": "Big Tech Corp",
        "job_apply_link": "https://bigtech.com/jobs/staff-react",
        "combined_score": 85,
        "seniority_level": "experienced",
    }
    job_internship = {
        "job_title": "React Frontend Intern",
        "company": "Startup Hub",
        "employer_name": "Startup Hub",
        "job_apply_link": "https://startuphub.com/internships/react",
        "combined_score": 80,
        "seniority_level": "internship",
    }

    ensure_job_identity(job_experienced)
    ensure_job_identity(job_internship)

    # Initial order: experienced first
    raw_list = [job_experienced, job_internship]

    # Candidate seeking internship: sorted so internship comes first
    sorted_list = sorted(raw_list, key=lambda j: 0 if j["seniority_level"] == "internship" else 1)
    for idx, j in enumerate(sorted_list):
        j["cache_id"] = idx
        GLOBAL_JOBS_REGISTRY[j["job_id"]] = j

    USER_JOBS_CACHE[auth_user.id] = sorted_list

    # Now sorted_list[0] is Startup Hub (Internship)
    assert sorted_list[0]["company"] == "Startup Hub"
    # sorted_list[1] is Big Tech Corp (Experienced)
    assert sorted_list[1]["company"] == "Big Tech Corp"

    # Click Apply on index 0 -> MUST go to Startup Hub
    resp_0 = client.get("/job/apply/0")
    assert resp_0.location == "https://startuphub.com/internships/react"

    # Click Apply on index 1 -> MUST go to Big Tech Corp
    resp_1 = client.get("/job/apply/1")
    assert resp_1.location == "https://bigtech.com/jobs/staff-react"

    # Click Apply by exact job_id for Big Tech -> MUST go to Big Tech Corp
    resp_bigtech = client.get(f"/job/apply/{job_experienced['job_id']}")
    assert resp_bigtech.location == "https://bigtech.com/jobs/staff-react"

    # Click Apply by exact job_id for Startup Hub -> MUST go to Startup Hub
    resp_startup = client.get(f"/job/apply/{job_internship['job_id']}")
    assert resp_startup.location == "https://startuphub.com/internships/react"

