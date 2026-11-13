import json
import unittest
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import LoginHistory, User
from app.services.auth_dataset import build_auth_hashmap, get_auth_dataset_summary


class TestAuthDatasetAndVercel(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def test_signup_stores_date_and_hashed_password(self):
        res = self.client.post(
            "/register",
            data={
                "name": "Jane Developer",
                "email": "jane@example.com",
                "password": "SecurePassword123!",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            user = User.query.filter_by(email="jane@example.com").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.name, "Jane Developer")
            # Password must NOT be stored in plain text
            self.assertNotEqual(user.password_hash, "SecurePassword123!")
            self.assertTrue(user.check_password("SecurePassword123!"))
            # Signup date (created_at) must be recorded
            self.assertIsNotNone(user.created_at)
            self.assertIsInstance(user.created_at, datetime)

            # Registration event must be recorded in login history
            history = LoginHistory.query.filter_by(email="jane@example.com").first()
            self.assertIsNotNone(history)
            self.assertEqual(history.status, "SUCCESS")

    def test_login_records_dates_and_increments_count(self):
        with self.app.app_context():
            user = User(name="John Doe", email="john@example.com")
            user.set_password("mypassword456")
            db.session.add(user)
            db.session.commit()

        # Perform login
        res = self.client.post(
            "/login",
            data={"email": "john@example.com", "password": "mypassword456"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            updated_user = User.query.filter_by(email="john@example.com").first()
            self.assertIsNotNone(updated_user.last_login)
            self.assertEqual(updated_user.login_count, 1)

            # Check history log
            log = LoginHistory.query.filter_by(email="john@example.com", status="SUCCESS").first()
            self.assertIsNotNone(log)
            self.assertIsNotNone(log.timestamp)

    def test_failed_login_records_failed_event(self):
        res = self.client.post(
            "/login",
            data={"email": "unknown@example.com", "password": "wrongpassword"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            log = LoginHistory.query.filter_by(email="unknown@example.com", status="FAILED").first()
            self.assertIsNotNone(log)
            self.assertEqual(log.failure_reason, "Account not registered")

    def test_auth_hashmap_dataset_structure(self):
        with self.app.app_context():
            user = User(name="Alice Data", email="alice@test.com")
            user.set_password("pass12345")
            db.session.add(user)
            db.session.commit()

            hashmap = build_auth_hashmap()
            self.assertIn("alice@test.com", hashmap)
            user_entry = hashmap["alice@test.com"]
            self.assertEqual(user_entry["name"], "Alice Data")
            self.assertTrue(user_entry["password_hash"].startswith(("scrypt:", "pbkdf2:")))
            self.assertIsNotNone(user_entry["signup_date"])

    def test_dataset_export_and_activity_routes(self):
        # Register and login a user
        self.client.post(
            "/register",
            data={"name": "Dev User", "email": "dev@test.com", "password": "password999"},
            follow_redirects=True,
        )
        self.client.post(
            "/login",
            data={"email": "dev@test.com", "password": "password999"},
            follow_redirects=True,
        )

        # Activity page
        res = self.client.get("/activity")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Login Activity", res.data)

        # Dataset view HTML
        res = self.client.get("/dataset")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"dev@test.com", res.data)

        # Dataset JSON API
        res = self.client.get("/dataset?format=json")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("users_hashmap", data)
        self.assertIn("dev@test.com", data["users_hashmap"])

        # Dataset export JSON file
        res = self.client.get("/export-dataset")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/json")

    def test_vercel_wsgi_entrypoint(self):
        from api.index import app as vercel_app
        self.assertIsNotNone(vercel_app)
        self.assertTrue(hasattr(vercel_app, "wsgi_app"))

    def test_production_wsgi_server_waitress(self):
        from waitress import serve
        self.assertTrue(callable(serve))

    def test_database_persistence_and_relationships(self):
        with self.app.app_context():
            # Create user
            user = User(name="Sam Smith", email="sam@test.com")
            user.set_password("mypassword")
            db.session.add(user)
            db.session.commit()

            # Record login event
            log = LoginHistory(
                user_id=user.id,
                email=user.email,
                status="SUCCESS",
                ip_address="192.168.1.50",
                user_agent="TestAgent/1.0",
                timestamp=datetime.utcnow(),
            )
            db.session.add(log)
            db.session.commit()

            # Query back from database
            retrieved = User.query.filter_by(email="sam@test.com").first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.name, "Sam Smith")
            self.assertEqual(len(retrieved.login_history), 1)
            self.assertEqual(retrieved.login_history[0].ip_address, "192.168.1.50")


if __name__ == "__main__":
    unittest.main()

