"""
Flask Application Factory.
Creates and configures the Flask application.

Security:
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- Rate limiting on sensitive endpoints
- Request size limits via MAX_CONTENT_LENGTH
- Generic 500 error messages (never leak stack traces)
"""
from flask import Flask, jsonify, request

from app.core.config import config_by_name
from app.core.extensions import db, migrate, jwt, babel, cors, ma


def create_app(config_name: str = 'development') -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_name: Configuration environment name ('development', 'testing', 'production')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register security middleware
    _register_security_middleware(app)

    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions with the app."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    babel.init_app(app)
    # CORS — restrict origins in production
    allowed_origins = app.config.get('CORS_ORIGINS', '*')
    cors.init_app(app, resources={r'/api/*': {'origins': allowed_origins}})
    ma.init_app(app)

    # JWT token blocklist hook
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.api.routes.auth import _is_token_revoked
        return _is_token_revoked(jwt_header, jwt_payload)

    # Expired / invalid JWT handlers — generic messages
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token has expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({'success': False, 'message': 'Invalid token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({'success': False, 'message': 'Authorization required'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token has been revoked'}), 401


def _register_blueprints(app: Flask) -> None:
    """Register API blueprints."""
    from app.api.routes.health import health_bp
    from app.api.routes.auth import auth_bp
    from app.api.routes.houses import houses_bp
    from app.api.routes.payments import payments_bp
    from app.api.routes.verification import verification_bp
    from app.api.routes.reports import reports_bp

    app.register_blueprint(health_bp, url_prefix='/api/v1')
    app.register_blueprint(auth_bp, url_prefix='/api/v1')
    app.register_blueprint(houses_bp, url_prefix='/api/v1')
    app.register_blueprint(payments_bp, url_prefix='/api/v1')
    app.register_blueprint(verification_bp, url_prefix='/api/v1')
    app.register_blueprint(reports_bp, url_prefix='/api/v1')


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': str(error.description)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({
            'success': False,
            'error': 'Payload Too Large',
            'message': 'Request body exceeds maximum allowed size'
        }), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        # NEVER leak stack traces to clients
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500


def _register_security_middleware(app: Flask) -> None:
    """Add security headers to every response."""

    @app.after_request
    def set_security_headers(response):
        # Prevent MIME-type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Enable XSS filter in older browsers
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Referrer policy — don't leak full URL
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Prevent caching of authenticated responses
        if 'Authorization' in request.headers:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        # Content Security Policy — API only serves JSON
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        # Permissions Policy — disable dangerous browser features
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response
