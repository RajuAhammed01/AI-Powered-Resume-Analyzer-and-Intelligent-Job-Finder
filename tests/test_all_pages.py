import unittest
from app import create_app
from app.extensions import db
from app.models import User, Resume, JobPreference, SavedJob

class TestResumeAIPages(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            user = User(name="Raju Ahammed", email="raju@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()

    def test_public_pages(self):
        # 1. Landing Page
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # 2. Login Page
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)

        # 3. Register Page
        res = self.client.get("/register")
        self.assertEqual(res.status_code, 200)

    def test_auth_flow_and_protected_pages(self):
        # Login
        res = self.client.post("/login", data={"email": "raju@example.com", "password": "password123"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 4. Dashboard
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)

        # 5. Upload Resume Page
        res = self.client.get("/upload")
        self.assertEqual(res.status_code, 200)

        # 7. Job Preferences Page
        res = self.client.get("/preferences")
        self.assertEqual(res.status_code, 200)

        # 8. Job Recommendations Page
        res = self.client.get("/results")
        self.assertEqual(res.status_code, 200)

        # 9. Job Detail Page
        res = self.client.get("/job/0")
        self.assertEqual(res.status_code, 200)

        # 10. Saved Jobs Page
        res = self.client.get("/saved-jobs")
        self.assertEqual(res.status_code, 200)

        # 11. Profile & Settings Page
        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
