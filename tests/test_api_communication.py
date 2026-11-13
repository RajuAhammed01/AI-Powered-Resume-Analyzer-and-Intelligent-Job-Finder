import json
import time
import pytest
from app import create_app
from app.extensions import db
from app.models import User, Resume, SavedJob, JobPreference
from app.services.api_client import ApiClient, CircuitBreaker, CircuitBreakerOpenError, default_api_client
from app.services.job_validator import GLOBAL_JOBS_REGISTRY


@pytest.fixture
def app_instance():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-api",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def authenticated_client(client, app_instance):
    with app_instance.app_context():
        user = User(
            email="api@jobsnap.test",
            name="API Test Candidate",
            title_role="Backend Developer",
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        # Add a resume with python and backend skills
        resume = Resume(
            user_id=user.id,
            filename="backend_cv.pdf",
            extracted_text="Experienced Backend Python Django PostgreSQL Docker developer building REST APIs",
            extracted_skills=json.dumps(["Python", "Django", "PostgreSQL", "Docker", "REST APIs"]),
            completeness_score=85,
        )
        db.session.add(resume)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    return client


def test_circuit_breaker_lifecycle():
    """Verify CircuitBreaker states: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker("TestProvider", failure_threshold=3, cooldown_seconds=0.1)

    # 1. Starts CLOSED
    assert cb.state == CircuitBreaker.STATE_CLOSED
    assert cb.can_execute() is True

    # 2. Trigger failures to reach threshold
    cb.record_failure(Exception("Timeout 1"))
    assert cb.state == CircuitBreaker.STATE_CLOSED
    cb.record_failure(Exception("HTTP 500"))
    assert cb.state == CircuitBreaker.STATE_CLOSED
    cb.record_failure(Exception("HTTP 503"))

    # Now state should be OPEN
    assert cb.state == CircuitBreaker.STATE_OPEN
    assert cb.can_execute() is False

    # 3. Wait for cooldown to expire
    time.sleep(0.15)
    assert cb.can_execute() is True  # Triggers transition to HALF_OPEN
    assert cb.state == CircuitBreaker.STATE_HALF_OPEN

    # 4. Successful recovery resets to CLOSED
    cb.record_success(duration_ms=45.0)
    assert cb.state == CircuitBreaker.STATE_CLOSED
    assert cb.failure_count == 0


def test_api_client_session_pooling_and_configuration():
    """Verify ApiClient initializes HTTP connection pools and retry adapters."""
    client_instance = ApiClient(pool_connections=15, pool_maxsize=30, max_retries=2)

    # Check session adapters for http and https
    adapter_https = client_instance.session.get_adapter("https://api.example.com")
    adapter_http = client_instance.session.get_adapter("http://api.example.com")

    assert adapter_https is not None
    assert adapter_http is not None
    assert adapter_https._pool_connections == 15
    assert adapter_https._pool_maxsize == 30

    # Check circuit breaker management
    cb = client_instance.get_circuit_breaker("RapidAPI")
    assert cb.name == "RapidAPI"
    assert "RapidAPI" in client_instance.get_all_breaker_metrics()


def test_api_health_endpoint(client):
    """Test /api/v1/health and unversioned alias /api/health."""
    for path in ["/api/v1/health", "/api/health"]:
        resp = client.get(path)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["status"] in ("healthy", "degraded")
        assert data["data"]["database"]["status"] == "healthy"
        assert "circuits" in data["data"]
        assert "cache" in data["data"]
        assert "latency_ms" in data["meta"]


def test_api_circuits_status(client):
    """Test /api/v1/circuits endpoint."""
    resp = client.get("/api/v1/circuits")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], dict)


def test_api_jobs_search(client):
    """Test /api/v1/jobs/search endpoint."""
    resp = client.get("/api/v1/jobs/search?q=Python&location=Remote&limit=5")
    assert resp.status_code == 200
    payload = resp.get_json()

    assert payload["success"] is True
    assert "data" in payload
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) > 0
    assert payload["meta"]["count"] <= 5
    assert "latency_ms" in payload["meta"]

    first_job = payload["data"][0]
    assert "job_title" in first_job
    assert "job_apply_link" in first_job
    assert "job_id" in first_job
    assert first_job["job_apply_link"].startswith("http")


def test_api_jobs_search_authenticated_scores(authenticated_client):
    """Test that authenticated users receive personalized resume match analysis in API responses."""
    resp = authenticated_client.get("/api/v1/jobs/search?q=Python&limit=3")
    assert resp.status_code == 200
    payload = resp.get_json()

    assert payload["success"] is True
    assert len(payload["data"]) > 0

    first_job = payload["data"][0]
    assert "match_score" in first_job
    assert "combined_score" in first_job
    assert isinstance(first_job["matched_skills"], list)
    assert isinstance(first_job["missing_skills"], list)


def test_api_get_job_by_id(client):
    """Test /api/v1/jobs/<job_id> lookup and 404 handling."""
    # Register a known test job in registry
    test_id = "test_api_job_001"
    GLOBAL_JOBS_REGISTRY[test_id] = {
        "job_id": test_id,
        "job_title": "Senior Cloud Architect",
        "company": "Amazon Web Services",
        "employer_name": "Amazon Web Services",
        "location": "Remote",
        "job_apply_link": "https://amazon.jobs/en/jobs/001",
        "job_skills": ["AWS", "Terraform", "Kubernetes"],
        "combined_score": 92,
    }

    # Successful retrieval
    resp = client.get(f"/api/v1/jobs/{test_id}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["data"]["job_id"] == test_id
    assert payload["data"]["job_title"] == "Senior Cloud Architect"

    # Not found retrieval
    resp_404 = client.get("/api/v1/jobs/non_existent_id_99999")
    assert resp_404.status_code == 404
    data_404 = resp_404.get_json()
    assert data_404["success"] is False
    assert data_404["error"]["code"] == "JOB_NOT_FOUND"


def test_api_content_negotiation_and_error_handling(client):
    """
    Ensure API routes and requests with Accept: application/json return
    JSON error envelopes instead of HTML error pages.
    """
    # 1. 404 on API route returns JSON
    resp_api = client.get("/api/v1/nonexistent-endpoint")
    assert resp_api.status_code == 404
    assert resp_api.is_json
    data = resp_api.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"

    # 2. Accept: application/json header on unknown path returns JSON
    resp_header = client.get("/some-random-broken-path", headers={"Accept": "application/json"})
    assert resp_header.status_code == 404
    assert resp_header.is_json
    data_header = resp_header.get_json()
    assert data_header["success"] is False
    assert data_header["error"]["code"] == "NOT_FOUND"


def test_api_save_and_unsave_job(authenticated_client):
    """Test asynchronous bookmarking and unsaving via /api/v1/jobs/save."""
    save_payload = {
        "job_id": "api_bookmark_role_1",
        "job_title": "Backend Systems Engineer",
        "company": "Stripe",
        "location": "Remote",
        "job_apply_link": "https://stripe.com/jobs/1",
    }

    # Save
    resp = authenticated_client.post("/api/v1/jobs/save", json=save_payload)
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["saved"] is True
    assert data["data"]["job_id"] == "api_bookmark_role_1"

    # Unsave / Delete
    resp_del = authenticated_client.delete("/api/v1/jobs/save/api_bookmark_role_1")
    assert resp_del.status_code == 200
    del_data = resp_del.get_json()
    assert del_data["success"] is True
    assert del_data["data"]["saved"] is False


def test_api_apply_intent(authenticated_client):
    """Test asynchronous apply intent recording."""
    payload = {
        "job_id": "intent_test_1",
        "job_title": "Full Stack Engineer",
        "company": "Linear",
        "job_apply_link": "https://linear.app/careers/1",
    }
    resp = authenticated_client.post("/api/v1/jobs/apply-intent", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["apply_url"] == "https://linear.app/careers/1"
    assert data["data"]["is_valid_url"] is True


def test_api_resume_skills(authenticated_client):
    """Test /api/v1/resume/skills returns user's extracted skills and profile."""
    resp = authenticated_client.get("/api/v1/resume/skills")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "skills" in data["data"]
    assert "Python" in data["data"]["skills"]
    assert "profile" in data["data"]
