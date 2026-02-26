"""
Security tests — verify all hardening measures work correctly.

Tests cover:
1. Bcrypt password hashing with salt rounds
2. Password complexity validation
3. Account lockout after failed attempts
4. XSS / HTML injection sanitization
5. Security headers on every response
6. JWT algorithm enforcement
7. Input validation (coordinates, numerics)
8. Payment method whitelist
9. Generic error messages (no user enumeration)
10. Request body size limit
"""
import pytest

from app.models.user import (
    User, BCRYPT_SALT_ROUNDS, MAX_FAILED_ATTEMPTS,
    validate_password_strength, PasswordValidationError,
)
from app.core.validators import (
    sanitize_string, sanitize_phone,
    validate_latitude, validate_longitude,
    validate_positive_int, validate_positive_float,
)


# ── 1. Bcrypt Password Hashing ──────────────────────────────────


class TestBcryptHashing:
    """Verify bcrypt is used with proper salt rounds."""

    def test_password_hash_is_bcrypt(self, app, db_session):
        user = User(username='hashtest', email='hash@test.cm', role='viewer')
        user.set_password('TestPass1!')
        db_session.add(user)
        db_session.commit()
        # bcrypt hashes always start with $2b$
        assert user.password_hash.startswith('$2b$')

    def test_salt_rounds_in_hash(self, app, db_session):
        user = User(username='salttest', email='salt@test.cm', role='viewer')
        user.set_password('TestPass1!')
        db_session.add(user)
        db_session.commit()
        # Hash format: $2b$<rounds>$...
        rounds = int(user.password_hash.split('$')[2])
        assert rounds == BCRYPT_SALT_ROUNDS

    def test_same_password_different_hashes(self, app, db_session):
        """Each hash gets a unique random salt."""
        u1 = User(username='u1', email='u1@test.cm', role='viewer')
        u2 = User(username='u2', email='u2@test.cm', role='viewer')
        u1.set_password('SamePass1!')
        u2.set_password('SamePass1!')
        assert u1.password_hash != u2.password_hash

    def test_check_password_succeeds(self, app, db_session):
        user = User(username='chk', email='chk@test.cm', role='viewer')
        user.set_password('Correct1!')
        assert user.check_password('Correct1!') is True

    def test_check_password_fails(self, app, db_session):
        user = User(username='chk2', email='chk2@test.cm', role='viewer')
        user.set_password('Correct1!')
        assert user.check_password('wrong') is False

    def test_empty_hash_always_fails(self, app, db_session):
        user = User(username='empty', email='empty@test.cm', role='viewer')
        assert user.check_password('anything') is False


# ── 2. Password Complexity ──────────────────────────────────────


class TestPasswordComplexity:
    """Validate OWASP-aligned password rules."""

    def test_valid_strong_password(self):
        # Should not raise
        validate_password_strength('MyStr0ng!Pass')

    def test_too_short_rejected(self):
        with pytest.raises(PasswordValidationError, match='at least 8'):
            validate_password_strength('Ab1!')

    def test_no_uppercase_rejected(self):
        with pytest.raises(PasswordValidationError, match='uppercase'):
            validate_password_strength('lowercase1!')

    def test_no_lowercase_rejected(self):
        with pytest.raises(PasswordValidationError, match='lowercase'):
            validate_password_strength('UPPERCASE1!')

    def test_no_digit_rejected(self):
        with pytest.raises(PasswordValidationError, match='digit'):
            validate_password_strength('NoDigitsHere!')

    def test_no_special_char_rejected(self):
        with pytest.raises(PasswordValidationError, match='special'):
            validate_password_strength('NoSpecial1a')

    def test_set_password_with_validation(self, app, db_session):
        user = User(username='valtest', email='val@test.cm', role='viewer')
        with pytest.raises(PasswordValidationError):
            user.set_password('weak', validate=True)

    def test_set_password_without_validation(self, app, db_session):
        user = User(username='noval', email='noval@test.cm', role='viewer')
        # Should NOT raise even for weak password when validate=False
        user.set_password('weak')
        assert user.check_password('weak')


# ── 3. Account Lockout ──────────────────────────────────────────


class TestAccountLockout:
    """Verify brute-force protection via lockout."""

    def test_account_locks_after_max_attempts(self, client, db_session):
        user = User(username='locktest', email='lock@test.cm', role='viewer')
        user.set_password('Correct1!')
        db_session.add(user)
        db_session.commit()

        # Fail MAX_FAILED_ATTEMPTS times
        for _ in range(MAX_FAILED_ATTEMPTS):
            resp = client.post('/api/v1/auth/login', json={
                'username': 'locktest', 'password': 'WRONG',
            })
            assert resp.status_code == 401

        # Next attempt should get 429 (locked)
        resp = client.post('/api/v1/auth/login', json={
            'username': 'locktest', 'password': 'Correct1!',
        })
        assert resp.status_code == 429
        assert 'locked' in resp.json['message'].lower()

    def test_successful_login_resets_counter(self, client, db_session):
        user = User(username='resettest', email='reset@test.cm', role='viewer')
        user.set_password('Good1Pass!')
        db_session.add(user)
        db_session.commit()

        # 2 failed attempts
        for _ in range(2):
            client.post('/api/v1/auth/login', json={
                'username': 'resettest', 'password': 'WRONG',
            })

        # Correct login
        resp = client.post('/api/v1/auth/login', json={
            'username': 'resettest', 'password': 'Good1Pass!',
        })
        assert resp.status_code == 200

        # Counter should be reset — next fail starts from 0
        db_session.refresh(user)
        assert user.failed_login_attempts == 0


# ── 4. XSS / Injection Sanitization ────────────────────────────


class TestInputSanitization:
    """Verify HTML/script tags are stripped from all inputs."""

    def test_xss_in_owner_name_stripped(self, client, auth_headers, db_session):
        from app.models import TaxCategory
        cat = TaxCategory(code='RES', name_fr='Res', name_en='Res', base_rate_per_sqm=500)
        db_session.add(cat)
        db_session.commit()

        resp = client.post('/api/v1/houses', headers=auth_headers, json={
            'commune': 'Yaounde I',
            'region': 'Centre',
            'owner_name': '<script>alert("xss")</script>Jean',
            'tax_category_code': 'RES',
            'coordinates': {'latitude': 3.8667, 'longitude': 11.5167},
        })
        assert resp.status_code == 201
        # Script tags must be stripped
        assert '<script>' not in resp.json['data']['owner_name']
        assert 'alert' not in resp.json['data']['owner_name']
        assert 'Jean' in resp.json['data']['owner_name']

    def test_html_injection_in_update(self, client, auth_headers, db_session):
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        from app.models import House

        house = House(
            immatriculation_number='CMR-CE-YDE1-0000099',
            commune='Yaounde I', region='Centre',
            geom=from_shape(Point(11.5167, 3.8667), srid=4326),
        )
        db_session.add(house)
        db_session.commit()

        resp = client.put(f'/api/v1/houses/{house.house_id}', headers=auth_headers, json={
            'owner_name': '<b>Bold</b> & "quotes"',
            'quartier': '<img src=x onerror=alert(1)>',
        })
        assert resp.status_code == 200
        assert '<b>' not in resp.json['data']['owner_name']
        assert '<img' not in resp.json['data'].get('quartier', '')

    def test_sanitize_string_strips_tags(self):
        assert sanitize_string('<script>alert(1)</script>hello') == 'hello'
        assert sanitize_string('<b>bold</b>') == 'bold'

    def test_sanitize_string_max_length(self):
        assert len(sanitize_string('a' * 500, 100)) == 100

    def test_sanitize_phone(self):
        assert sanitize_phone('+237 699-123-456') == '+237 699-123-456'
        assert sanitize_phone('<script>hack</script>') == ''


# ── 5. Security Headers ────────────────────────────────────────


class TestSecurityHeaders:
    """Verify OWASP-recommended headers on every response."""

    def test_x_content_type_options(self, client):
        resp = client.get('/api/v1/health')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options(self, client):
        resp = client.get('/api/v1/health')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_xss_protection(self, client):
        resp = client.get('/api/v1/health')
        assert '1; mode=block' in resp.headers.get('X-XSS-Protection', '')

    def test_content_security_policy(self, client):
        resp = client.get('/api/v1/health')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "default-src 'none'" in csp

    def test_referrer_policy(self, client):
        resp = client.get('/api/v1/health')
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_permissions_policy(self, client):
        resp = client.get('/api/v1/health')
        assert 'geolocation=()' in resp.headers.get('Permissions-Policy', '')


# ── 6. JWT Security ────────────────────────────────────────────


class TestJWTSecurity:
    """Verify JWT hardening."""

    def test_jwt_algorithm_pinned(self, app):
        assert app.config['JWT_ALGORITHM'] == 'HS256'
        assert app.config['JWT_DECODE_ALGORITHMS'] == ['HS256']

    def test_access_token_short_lived(self, app):
        # Testing config uses 5 min
        assert app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds() <= 300

    def test_expired_token_generic_message(self, client):
        resp = client.get('/api/v1/auth/me', headers={
            'Authorization': 'Bearer invalid.token.here'
        })
        assert resp.status_code == 401
        # Should not leak internal details
        assert 'traceback' not in resp.json.get('message', '').lower()


# ── 7. Input Validation ────────────────────────────────────────


class TestInputValidation:
    """Verify numeric and coordinate validation."""

    def test_validate_latitude_valid(self):
        assert validate_latitude(3.8667) == 3.8667
        assert validate_latitude(-90) == -90.0
        assert validate_latitude(90) == 90.0

    def test_validate_latitude_invalid(self):
        assert validate_latitude(91) is None
        assert validate_latitude(-91) is None
        assert validate_latitude('abc') is None

    def test_validate_longitude_valid(self):
        assert validate_longitude(11.5167) == 11.5167

    def test_validate_longitude_invalid(self):
        assert validate_longitude(181) is None

    def test_validate_positive_int(self):
        assert validate_positive_int(5) == 5
        assert validate_positive_int(-1) is None
        assert validate_positive_int(0) is None
        assert validate_positive_int('abc') is None

    def test_validate_positive_float(self):
        assert validate_positive_float(150.5) == 150.5
        assert validate_positive_float(-1) is None


# ── 8. Payment Method Whitelist ─────────────────────────────────


class TestPaymentMethodWhitelist:
    """Verify only valid payment methods are accepted."""

    def test_invalid_payment_method_rejected(self, client, auth_headers, db_session):
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        from app.models import House

        house = House(
            immatriculation_number='CMR-CE-YDE1-0000077',
            commune='Yaounde I', region='Centre',
            geom=from_shape(Point(11.5167, 3.8667), srid=4326),
            annual_tax_amount=50000,
        )
        db_session.add(house)
        db_session.commit()

        resp = client.post('/api/v1/payments', headers=auth_headers, json={
            'house_id': house.house_id,
            'amount_paid': 25000,
            'payment_method': 'BITCOIN',
            'payment_year': 2026,
        })
        assert resp.status_code == 400
        assert 'invalid' in resp.json['message'].lower() or 'Invalid' in resp.json['message']


# ── 9. User Enumeration Protection ─────────────────────────────


class TestUserEnumeration:
    """Verify login doesn't reveal whether a username exists."""

    def test_nonexistent_user_same_message(self, client, db_session):
        resp = client.post('/api/v1/auth/login', json={
            'username': 'does_not_exist', 'password': 'anything',
        })
        assert resp.status_code == 401
        assert resp.json['message'] == 'Invalid credentials'

    def test_wrong_password_same_message(self, client, db_session):
        user = User(username='enumtest', email='enum@test.cm', role='viewer')
        user.set_password('RealPass1!')
        db_session.add(user)
        db_session.commit()

        resp = client.post('/api/v1/auth/login', json={
            'username': 'enumtest', 'password': 'wrong',
        })
        assert resp.status_code == 401
        assert resp.json['message'] == 'Invalid credentials'


# ── 10. Max Content Length ──────────────────────────────────────


class TestMaxContentLength:
    """Verify config enforces body size limit."""

    def test_max_content_length_configured(self, app):
        assert app.config['MAX_CONTENT_LENGTH'] is not None
        # Should be <= 10 MB
        assert app.config['MAX_CONTENT_LENGTH'] <= 10 * 1024 * 1024
