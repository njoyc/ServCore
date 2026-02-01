import os
from datetime import timedelta


class BaseConfig:
    """
    Base configuration shared across environments
    """
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session / security
    SESSION_COOKIE_NAME = "servcore_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
class DevelopmentConfig(BaseConfig):
    """
    Local development configuration
    """
    DEBUG = True

    # Explicit SQLite location (no ambiguity)
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "dev.db")
    )

    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    """
    Production configuration (Render / Railway / etc.)
    """
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_ECHO = False

    # Database URL handling (Render / Heroku compatibility)
    _db_url = os.environ.get("DATABASE_URL")

    if _db_url and _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url

    @staticmethod
    def init_app(app):
        # HARD FAIL if secrets are missing in production
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY environment variable must be set in production")

        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production")


# Config registry
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
