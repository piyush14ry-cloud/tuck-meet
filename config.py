"""Application configuration, loaded entirely from environment variables.

No secrets are hard-coded. Copy .env.example to .env for local development.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = ENV == "development"

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tuckmeet.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Access control ---
    ALLOWED_EMAIL_DOMAIN = os.environ.get("ALLOWED_EMAIL_DOMAIN", "tuck.dartmouth.edu").lower()

    # --- Email ---
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "stub").lower()
    MAIL_FROM = os.environ.get("MAIL_FROM", "tuckmeet@tuck.dartmouth.edu")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _bool("SMTP_USE_TLS", True)

    # --- Matching ---
    REMATCH_COOLDOWN_DAYS = int(os.environ.get("REMATCH_COOLDOWN_DAYS", "21"))
    MATCHING_TRIGGER_TOKEN = os.environ.get("MATCHING_TRIGGER_TOKEN", "")

    # --- Session / cookie hardening ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only send cookies over HTTPS in production.
    SESSION_COOKIE_SECURE = ENV == "production"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours

    # WTForms/Flask-WTF CSRF protection is on by default.
    WTF_CSRF_TIME_LIMIT = None


def validate(config: type[Config]) -> None:
    """Fail fast on missing critical secrets in production."""
    if not config.SECRET_KEY:
        if config.ENV == "production":
            raise RuntimeError("SECRET_KEY must be set in production.")
        # Dev convenience only: ephemeral key (sessions reset on restart).
        config.SECRET_KEY = "dev-only-insecure-key-do-not-use-in-prod"
