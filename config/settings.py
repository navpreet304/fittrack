import os
from dotenv import load_dotenv

load_dotenv()


def _build_database_url(default_host: str = "localhost", default_port: str = "5432") -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    user = os.getenv("POSTGRES_USER", "fittrack")
    password = os.getenv("POSTGRES_PASSWORD", "")
    database = os.getenv("POSTGRES_DB", "fittrackdb")
    host = os.getenv("POSTGRES_HOST", default_host)
    port = os.getenv("POSTGRES_PORT", default_port)
    credentials = f"{user}:{password}" if password else user
    return f"postgresql://{credentials}@{host}:{port}/{database}"


class Config:
    DATABASE_URL = _build_database_url()
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-fittrack-change-in-production!!")
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    NUTRITION_API_URL = os.getenv("NUTRITION_API_URL", "https://api.nutritionix.com/v1_1")
    NUTRITION_API_KEY = os.getenv("NUTRITION_API_KEY", "")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    CACHE_DIR = os.getenv("CACHE_DIR", ".cache/nutrition")
    TESTING = False
    DEBUG = False


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    if env == "testing":
        return TestConfig()
    return DevConfig()
