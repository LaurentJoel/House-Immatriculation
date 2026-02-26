"""
Tests for Flask application factory (Step 1.4).
"""
from app import create_app


def test_app_creation(app):
    """Test that the app is created successfully."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_app_has_extensions(app):
    """Test that all extensions are initialized."""
    assert 'sqlalchemy' in app.extensions
    assert 'migrate' in app.extensions


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'Immatriculation API'


def test_404_handler(client):
    """Test 404 error handler returns JSON."""
    response = client.get('/api/v1/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
