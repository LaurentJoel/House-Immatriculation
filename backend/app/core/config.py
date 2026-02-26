"""
Application configuration for different environments.

Security notes:
- SECRET_KEY & JWT_SECRET_KEY MUST be overridden via env vars in production
- JWT algorithm pinned to HS256 to prevent algorithm-confusion attacks
- MAX_CONTENT_LENGTH limits request body to 10 MB
- CORS origins restricted in production
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Base configuration shared across all environments."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Request body size limit (10 MB) — prevents zip-bomb / large-payload DoS
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg://immat_user:immat_dev_password@localhost:5433/immatriculation'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # JWT — security-hardened
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)   # Shortened from 1 h
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)      # Shortened from 30 d
    JWT_TOKEN_LOCATION = ['headers']
    JWT_ALGORITHM = 'HS256'                            # Pin algorithm
    JWT_DECODE_ALGORITHMS = ['HS256']                  # Reject all others

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # MinIO
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'immatriculation')

    # Babel / i18n
    BABEL_DEFAULT_LOCALE = 'fr'
    BABEL_DEFAULT_TIMEZONE = 'Africa/Douala'
    LANGUAGES = {'fr': 'Francais', 'en': 'English'}

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # Rate limiting (Flask-Limiter)
    RATELIMIT_DEFAULT = '200/hour'
    RATELIMIT_STORAGE_URI = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    # More permissive token lifetime for dev convenience
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class TestingConfig(BaseConfig):
    """Testing configuration."""

    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql+psycopg://immat_user:immat_dev_password@localhost:5433/immatriculation_test'
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False
    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    # In production the following MUST come from env vars:
    # SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL, REDIS_URL


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
