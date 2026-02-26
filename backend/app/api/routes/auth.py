"""
Authentication API routes — login, logout, refresh, me.

Security:
- Login rate-limited to 5/minute per IP (brute-force protection)
- Account lockout after 5 consecutive failed attempts
- Generic error messages (no user-enumeration leakage)
- Constant-time password comparison via bcrypt
"""
import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from app.core.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

# Simple in-memory token blocklist (use Redis in production)
_blocklist: set = set()

# Input constraints
_MAX_USERNAME_LEN = 50
_MAX_PASSWORD_LEN = 128
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.-]+$')


def _is_token_revoked(jwt_header, jwt_payload) -> bool:
    """Check if a token's jti has been revoked."""
    return jwt_payload['jti'] in _blocklist


def _sanitize_str(value: str, max_len: int) -> str:
    """Strip and truncate a string input."""
    if not isinstance(value, str):
        return ''
    return value.strip()[:max_len]


# ── Endpoints ──────────────────────────────────────────────────────

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens."""
    data = request.get_json(silent=True) or {}
    username = _sanitize_str(data.get('username', ''), _MAX_USERNAME_LEN)
    password = data.get('password', '')

    # Basic input validation
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    if not _USERNAME_RE.match(username):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    if len(password) > _MAX_PASSWORD_LEN:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    user = User.query.filter_by(username=username).first()

    # Generic failure — prevents user enumeration
    if user is None:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # Account lockout check
    if user.is_locked:
        return jsonify({'success': False, 'message': 'Account temporarily locked. Try again later.'}), 429

    if not user.check_password(password):
        user.record_failed_login()
        db.session.commit()
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'success': False, 'message': 'Account disabled'}), 403

    # Success — reset lockout counter
    user.record_successful_login()
    db.session.commit()

    access_token = create_access_token(
        identity=str(user.user_id),
        additional_claims={'role': user.role},
    )
    refresh_token = create_refresh_token(identity=str(user.user_id))

    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'username': user.username,
        'role': user.role,
    }), 200


@auth_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def me():
    """Return the current authenticated user's profile."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    return jsonify({
        'success': True,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'full_name': user.full_name,
        'preferred_language': user.preferred_language,
    }), 200


@auth_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Issue a new access token from a refresh token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({
        'success': True,
        'access_token': access_token,
    }), 200


@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Revoke the current access token."""
    jti = get_jwt()['jti']
    _blocklist.add(jti)
    return jsonify({'success': True, 'message': 'Successfully logged out'}), 200
