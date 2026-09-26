import os

from dotenv import load_dotenv

load_dotenv()


class Config:
	SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
	SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
	MAX_CONTENT_LENGTH = 5 * 1024 * 1024
