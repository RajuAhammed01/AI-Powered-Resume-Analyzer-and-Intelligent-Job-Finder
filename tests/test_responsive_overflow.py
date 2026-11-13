import unittest
import os
import re
from app import create_app
from app.extensions import db
from app.models import User, Resume, JobPreference, SavedJob

class TestResponsiveOverflow(unittest.TestCase):
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
            user = User(name="Test User", email="test@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

            resume = Resume(
                user_id=user.id,
                filename="test_candidate_resume.pdf",
                extracted_skills='["Python", "FastAPI", "SQL"]',
                extracted_text="Python and backend engineer.",
                completeness_score=88,
            )
            db.session.add(resume)
            pref = JobPreference(user_id=user.id, target_role="Software Engineer", location="Remote")
            db.session.add(pref)
            db.session.commit()

    def test_css_overflow_guard_rules(self):
        css_path = os.path.join(self.app.root_path, "static", "css", "style.css")
        self.assertTrue(os.path.exists(css_path), "style.css must exist")
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # Check essential overflow prevention rules
        self.assertIn("overflow-x: hidden", css_content, "CSS must have overflow-x: hidden on html/body/layout")
        self.assertIn("max-width: 100%", css_content, "CSS must constrain element widths to 100%")
        self.assertIn(".responsive-split-grid", css_content, "CSS must define responsive split grid system")
        self.assertIn(".funnel-pipeline-grid", css_content, "CSS must define responsive funnel pipeline")
        self.assertIn(".table-responsive", css_content, "CSS must define responsive table container")
        self.assertIn(".main-wrapper", css_content)
        self.assertIn("max-width: calc(100% - 260px)", css_content, "main-wrapper must respect sidebar boundary on desktop")

    def test_pages_render_with_responsive_classes(self):
        # Login
        self.client.post("/login", data={"email": "test@example.com", "password": "password123"}, follow_redirects=True)

        pages = ["/dashboard", "/results", "/upload", "/preferences", "/profile", "/saved-jobs"]
        for page in pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200, f"Page {page} failed to render")
            html = res.get_data(as_text=True)

            # Ensure none of the pages have old unconstrained inline grid templates that force overflow
            self.assertNotIn("grid-template-columns: 1.2fr 0.8fr;", html, f"Page {page} still has rigid inline 1.2fr 0.8fr grid")
            self.assertNotIn("grid-template-columns: 1.3fr 0.7fr;", html, f"Page {page} still has rigid inline 1.3fr 0.7fr grid")

    def test_dashboard_funnel_responsive(self):
        self.client.post("/login", data={"email": "test@example.com", "password": "password123"}, follow_redirects=True)
        res = self.client.get("/dashboard")
        html = res.get_data(as_text=True)
        self.assertIn("funnel-pipeline-grid", html, "Dashboard must use responsive funnel-pipeline-grid")
        self.assertIn("funnel-chevron", html, "Dashboard chevrons must use funnel-chevron class for responsive visibility")

    def test_upload_table_responsive_wrapper(self):
        self.client.post("/login", data={"email": "test@example.com", "password": "password123"}, follow_redirects=True)
        res = self.client.get("/upload")
        html = res.get_data(as_text=True)
        self.assertIn("table-responsive", html, "Upload page table must be wrapped in table-responsive container")

    def test_education_snapshot_overflow_prevention(self):
        with self.app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            r = Resume.query.filter_by(user_id=user.id).first()
            r.education = (
                "University of Liberal Arts Bangladesh (ULAB)\n"
                "Bachelor of Science in Computer Science and Engineering\n"
                "Jun 1, 2024 – Present | Expected Graduation: 2029\n"
                "RELEVANT COURSEWORK\n"
                "Data Structures & Algorithms • Database Management Systems • OOP"
            )
            db.session.commit()

        self.client.post("/login", data={"email": "test@example.com", "password": "password123"}, follow_redirects=True)
        res = self.client.get("/dashboard")
        html = res.get_data(as_text=True)

        # Check that clean degree is rendered without the bloated coursework line
        self.assertIn("University of Liberal Arts Bangladesh (ULAB)", html)
        self.assertIn("Bachelor of Science in Computer Science", html)
        self.assertNotIn("RELEVANT COURSEWORK", html)
        self.assertIn("resume-snapshot-meta", html)

if __name__ == "__main__":
    unittest.main()

