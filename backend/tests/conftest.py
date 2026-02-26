"""
Pytest configuration and shared fixtures.
"""
import pytest

from app import create_app
from app.core.extensions import db as _db
from app.models.user import User


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    return app


@pytest.fixture(scope='session')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create a fresh database session for each test."""
    with app.app_context():
        _db.create_all()
        yield _db.session
        _db.session.rollback()
        _db.drop_all()


# ── Auth helper fixtures ──────────────────────────────────────

def _create_test_user(session, username='admin', password='admin123', role='super_admin'):
    """Persist a test user and return it."""
    user = User(username=username, email=f'{username}@gov.cm', role=role)
    user.set_password(password)
    session.add(user)
    session.commit()
    return user


@pytest.fixture()
def auth_headers(client, db_session):
    """Login as a super_admin and return Authorization headers."""
    _create_test_user(db_session)
    resp = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'admin123',
    })
    token = resp.json['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def agent_headers(client, db_session):
    """Login as a field_agent and return Authorization headers."""
    _create_test_user(db_session, username='agent', password='agent123', role='field_agent')
    resp = client.post('/api/v1/auth/login', json={
        'username': 'agent', 'password': 'agent123',
    })
    token = resp.json['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def refresh_headers(client, db_session):
    """Login and return headers with the refresh token."""
    _create_test_user(db_session)
    resp = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'admin123',
    })
    token = resp.json['refresh_token']
    return {'Authorization': f'Bearer {token}'}
