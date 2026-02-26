"""
Integration tests for Authentication API (Step 4.1).
"""
from tests.conftest import _create_test_user


class TestAuthAPI:
    """Step 4.1: Auth endpoint tests."""

    def test_login_success(self, client, db_session):
        _create_test_user(db_session, username='admin', password='admin123')
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin', 'password': 'admin123',
        })
        assert response.status_code == 200
        assert 'access_token' in response.json
        assert 'refresh_token' in response.json

    def test_login_wrong_password(self, client, db_session):
        _create_test_user(db_session, username='admin', password='admin123')
        response = client.post('/api/v1/auth/login', json={
            'username': 'admin', 'password': 'wrong',
        })
        assert response.status_code == 401

    def test_protected_route_without_token(self, client, db_session):
        response = client.get('/api/v1/auth/me')
        assert response.status_code == 401

    def test_protected_route_with_token(self, client, auth_headers):
        response = client.get('/api/v1/auth/me', headers=auth_headers)
        assert response.status_code == 200
        assert 'username' in response.json

    def test_token_refresh(self, client, refresh_headers):
        response = client.post('/api/v1/auth/refresh', headers=refresh_headers)
        assert response.status_code == 200
        assert 'access_token' in response.json

    def test_logout(self, client, auth_headers):
        response = client.post('/api/v1/auth/logout', headers=auth_headers)
        assert response.status_code == 200
