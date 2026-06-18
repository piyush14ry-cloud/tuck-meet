import pytest

from app import create_app
from app.extensions import db as _db
from config import Config


class TestConfig(Config):
    ENV = "testing"
    DEBUG = False
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    EMAIL_BACKEND = "stub"
    ALLOWED_EMAIL_DOMAIN = "tuck.dartmouth.edu"
    REMATCH_COOLDOWN_DAYS = 21
    MATCHING_TRIGGER_TOKEN = "test-token"
    SESSION_COOKIE_SECURE = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
