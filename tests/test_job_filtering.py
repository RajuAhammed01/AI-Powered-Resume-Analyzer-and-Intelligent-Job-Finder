import json
import unittest
from app import create_app
from app.extensions import db
from app.models import User, Resume, JobPreference, SavedJob

class TestJobFiltering(unittest.TestCase):
    def setUp(self):
        self.app = create_app(test_config={
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(name="Filter Tester", email="filter@example.com")
            user.set_password("SecurePassword123!")
            db.session.add(user)
            db.session.commit()

            resume = Resume(
                user_id=user.id,
                filename="filter_cv.pdf",
                extracted_skills=json.dumps(["Python", "React", "Docker", "SQL", "TypeScript", "FastAPI"]),
                extracted_text="Full Stack Engineer skilled in Python, React, Docker, SQL, and FastAPI.",
                experience="Software Engineer at TechStudio (2022-2025)",
                education="B.S. in Computer Science",
                completeness_score=90,
            )
            pref = JobPreference(
                user_id=user.id,
                target_role="Full Stack Developer",
                location="Remote",
            )
            db.session.add_all([resume, pref])
            db.session.commit()

            # Log in
            self.client.post("/login", data={"email": "filter@example.com", "password": "SecurePassword123!"})

    def test_results_page_contains_advanced_filters(self):
        res = self.client.get("/results")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 1. Advanced filter controls present
        self.assertIn("filter-domain", html)
        self.assertIn("filter-seniority", html)
        self.assertIn("filter-score", html)
        self.assertIn("filter-location", html)
        self.assertIn("filter-type", html)
        self.assertIn("filter-source", html)
        self.assertIn("sort-select", html)

        # 2. Dynamic skill pills and active chips bar present
        self.assertIn("Quick Skills:", html)
        self.assertIn("filter-skill-btn", html)
        self.assertIn("active-filters-container", html)
        self.assertIn("reset-filters-btn", html)
        self.assertIn("visible-jobs-count", html)

        # 3. Job cards contain rich multi-attribute dataset hooks
        self.assertIn("data-seniority=", html)
        self.assertIn("data-domain=", html)
        self.assertIn("data-score=", html)
        self.assertIn("data-skills=", html)

    def test_server_side_filtering_by_domain_and_seniority(self):
        # Filter by domain
        res_domain = self.client.get("/results?domain=backend")
        self.assertEqual(res_domain.status_code, 200)
        html_domain = res_domain.get_data(as_text=True)
        self.assertIn("Live Job Recommendations", html_domain)

        # Filter by seniority
        res_intern = self.client.get("/results?seniority=internship")
        self.assertEqual(res_intern.status_code, 200)
        html_intern = res_intern.get_data(as_text=True)
        self.assertIn("Live Job Recommendations", html_intern)

        # Filter by score
        res_score = self.client.get("/results?min_score=70")
        self.assertEqual(res_score.status_code, 200)

        # Sort by title
        res_sort = self.client.get("/results?sort=title")
        self.assertEqual(res_sort.status_code, 200)

if __name__ == "__main__":
    unittest.main()

