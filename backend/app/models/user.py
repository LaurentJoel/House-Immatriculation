"""
User model for authentication and authorization.

Security features:
- bcrypt password hashing with configurable salt rounds (default 12)
- Password complexity validation
- Account lockout after repeated failed logins
"""
import re
from datetime import datetime, timedelta, timezone

import bcrypt

from app.core.extensions import db

# ── Security constants ────────────────────────────────────────────
# Bcrypt cost factor (OWASP recommends >= 10; 12 is a good balance).
BCRYPT_SALT_ROUNDS = 12

# Password complexity
MIN_PASSWORD_LENGTH = 8
PASSWORD_SPECIAL_CHARS = r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]'

# Account lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class PasswordValidationError(ValueError):
    """Raised when a password does not meet complexity requirements."""


def validate_password_strength(password: str) -> None:
    """Enforce OWASP-aligned password complexity rules.

    Requires: >= 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special.
    Raises PasswordValidationError on failure.
    """
    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')
    if not re.search(r'[a-z]', password):
        errors.append('Must contain at least one lowercase letter.')
    if not re.search(r'[A-Z]', password):
        errors.append('Must contain at least one uppercase letter.')
    if not re.search(r'\d', password):
        errors.append('Must contain at least one digit.')
    if not re.search(PASSWORD_SPECIAL_CHARS, password):
        errors.append('Must contain at least one special character.')
    if errors:
        raise PasswordValidationError(' '.join(errors))


class User(db.Model):
    """User model for system authentication."""

    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False, default='')
    full_name = db.Column(db.String(100), nullable=True)
    role = db.Column(
        db.String(20),
        nullable=False,
        default='viewer'
    )
    preferred_language = db.Column(db.String(2), nullable=False, default='fr')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    assigned_region = db.Column(db.String(50), nullable=True)
    assigned_commune = db.Column(db.String(50), nullable=True)

    # Security tracking columns
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    password_changed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    verifications = db.relationship('VerificationHistory', backref='verified_by_user', lazy='dynamic')

    VALID_ROLES = ('super_admin', 'regional_admin', 'communal_admin', 'field_agent', 'tax_collector', 'viewer')

    # ── Password management ───────────────────────────────────────

    def set_password(self, password: str, *, validate: bool = False) -> None:
        """Hash and set the user password using bcrypt with salt rounds.

        Args:
            password: Plain-text password.
            validate: If True, enforce complexity rules first.
        """
        if validate:
            validate_password_strength(password)
        salt = bcrypt.gensalt(rounds=BCRYPT_SALT_ROUNDS)
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), salt
        ).decode('utf-8')
        self.password_changed_at = datetime.now(timezone.utc)

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored bcrypt hash."""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8'),
        )

    # ── Account lockout ───────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """Return True if the account is temporarily locked out."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_failed_login(self) -> None:
        """Increment failed attempts; lock account if threshold exceeded."""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            self.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )

    def record_successful_login(self) -> None:
        """Reset failed attempts counter and update last_login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
