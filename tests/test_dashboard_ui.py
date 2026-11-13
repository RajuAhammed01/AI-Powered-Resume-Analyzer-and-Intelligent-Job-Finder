import unittest
from app import create_app
from app.extensions import db
from app.models import User, Resume, JobPreference, SavedJob

class TestDashboardUI(unittest.TestCase):
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
            user = User(name="Alex Morgan", email="alex@enterprise.com")
            user.set_password("SecurePass123!")
            db.session.add(user)
            db.session.commit()

            resume = Resume(
                user_id=user.id,
                filename="Alex_Morgan_Resume.pdf",
                extracted_skills='["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]',
                extracted_text="Experienced Software Engineer with Python, FastAPI, Docker, and AWS skills.",
                education="B.S. in Computer Science, Tech University, 2021",
                experience="Senior Backend Engineer at CloudCorp (2021-Present)",
                contact_info="alex@enterprise.com | +1 555-0199",
                completeness_score=92,
            )
            db.session.add(resume)

            pref = JobPreference(user_id=user.id, target_role="Backend Engineer", location="Remote")
            db.session.add(pref)

            saved = SavedJob(
                user_id=user.id,
                job_title="Senior Python Engineer",
                company="NexusTech",
                status="saved",
            )
            applied = SavedJob(
                user_id=user.id,
                job_title="Backend Developer",
                company="DataFlow",
                status="applied",
            )
            db.session.add_all([saved, applied])
            db.session.commit()

    def test_dashboard_redesign_components_and_no_upgrade(self):
        # 1. Login
        login_res = self.client.post(
            "/login",
            data={"email": "alex@enterprise.com", "password": "SecurePass123!"},
            follow_redirects=True,
        )
        self.assertEqual(login_res.status_code, 200)

        # 2. Get Dashboard
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # 3. Sidebar Requirements
        self.assertIn("Dashboard", html)
        self.assertIn("Upload Resume", html)
        self.assertIn("Job Recommendations", html)
        self.assertIn("Saved Jobs", html)
        self.assertIn("Job Preferences", html)
        self.assertIn("Profile & Settings", html)
        self.assertIn("Logout", html)

        # Sidebar Promo / Upgrade Card from Reference Design
        self.assertIn("sidebar-promo-card", html)
        self.assertIn("Build your future", html)
        self.assertIn("Upgrade Plan", html)

        # 4. Top Navigation Bar Requirements
        self.assertIn("topbar-search-form", html)
        self.assertIn("topbar-search-input", html)
        self.assertIn("topbar-notification-btn", html)
        self.assertIn("Alex Morgan", html)
        self.assertIn("alex@enterprise.com", html)

        # 5. Welcome Section
        self.assertIn("Welcome back,", html)
        self.assertIn("Alex Morgan", html)
        self.assertIn("Live Matching Active", html)

        # 6. Dashboard Statistics (4 Metric Cards)
        self.assertIn("Resume Completeness", html)
        self.assertIn("Extracted Skills", html)
        self.assertIn("Top Match Score", html)
        self.assertIn("Tracked Jobs", html)
        self.assertIn("92%", html)

        # 7. Application Lifecycle Funnel
        self.assertIn("Application Lifecycle Funnel", html)
        self.assertIn("Bookmarked", html)
        self.assertIn("Applied", html)
        self.assertIn("Interviews", html)
        self.assertIn("Offers", html)

        # 8. Resume Snapshot Card
        self.assertIn("Resume Snapshot", html)
        self.assertIn("Alex_Morgan_Resume.pdf", html)
        self.assertIn("B.S. in Computer Science", html)
        self.assertIn("Senior Backend Engineer", html)
        self.assertIn("Python", html)
        self.assertIn("FastAPI", html)
        self.assertIn("View Match Analysis", html)

        # 9. Recommended Jobs Card
        self.assertIn("Recommended Jobs", html)

        # 10. Skill Gap Summary Card
        self.assertIn("Skill Gap Summary", html)

    def test_dashboard_empty_state_without_resume(self):
        # Create user without resume
        with self.app.app_context():
            user2 = User(name="Jane Doe", email="jane@enterprise.com")
            user2.set_password("SecurePass123!")
            db.session.add(user2)
            db.session.commit()

        login_res = self.client.post(
            "/login",
            data={"email": "jane@enterprise.com", "password": "SecurePass123!"},
            follow_redirects=True,
        )
        self.assertEqual(login_res.status_code, 200)

        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("No Resume Uploaded Yet", html)
        self.assertIn("Matching Is Not Active", html)
        self.assertIn("No Skill Gap Data Available", html)
        self.assertIn("sidebar-promo-card", html)

if __name__ == "__main__":
    unittest.main()

