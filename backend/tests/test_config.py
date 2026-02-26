"""
Tests for configuration management (Step 1.5).
"""
from app import create_app


def test_development_config():
    """Test development configuration."""
    app = create_app('development')
    assert app.config['DEBUG'] is True
    assert app.config['TESTING'] is False
    assert 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']


def test_testing_config():
    """Test testing configuration."""
    app = create_app('testing')
    assert app.config['TESTING'] is True
    assert app.config['DEBUG'] is False
    assert 'immatriculation_test' in app.config['SQLALCHEMY_DATABASE_URI']


def test_production_config():
    """Test production configuration."""
    app = create_app('production')
    assert app.config['DEBUG'] is False
    assert app.config['TESTING'] is False


def test_babel_config():
    """Test i18n default configuration."""
    app = create_app('testing')
    assert app.config['BABEL_DEFAULT_LOCALE'] == 'fr'
    assert app.config['LANGUAGES'] == {'fr': 'Francais', 'en': 'English'}
