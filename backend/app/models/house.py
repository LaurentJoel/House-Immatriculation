"""
House model - core entity of the immatriculation system.
"""
from datetime import datetime, timezone

from geoalchemy2 import Geometry

from app.core.extensions import db


class House(db.Model):
    """House model representing a registered building."""

    __tablename__ = 'houses'

    house_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    immatriculation_number = db.Column(
        db.String(25), unique=True, nullable=False, index=True
    )

    # Location
    commune = db.Column(db.String(50), nullable=False, index=True)
    department = db.Column(db.String(50), nullable=True)
    region = db.Column(db.String(50), nullable=False, index=True)
    quartier = db.Column(db.String(100), nullable=True)
    address_description = db.Column(db.Text, nullable=True)

    # Spatial
    geom = db.Column(Geometry('POINT', srid=4326), nullable=True)
    gps_latitude = db.Column(db.Numeric(10, 7), nullable=True)
    gps_longitude = db.Column(db.Numeric(10, 7), nullable=True)

    # Building characteristics
    building_type = db.Column(db.String(50), nullable=True)
    building_levels = db.Column(db.Integer, nullable=True, default=1)
    footprint_area = db.Column(db.Numeric(10, 2), nullable=True)
    total_built_area = db.Column(db.Numeric(10, 2), nullable=True)
    construction_year = db.Column(db.Integer, nullable=True)
    wall_material = db.Column(db.String(50), nullable=True)
    roof_material = db.Column(db.String(50), nullable=True)

    # Owner
    owner_name = db.Column(db.String(100), nullable=True)
    owner_national_id = db.Column(db.String(30), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)

    # Tax
    tax_category_id = db.Column(
        db.Integer,
        db.ForeignKey('tax_categories.category_id'),
        nullable=True
    )
    annual_tax_amount = db.Column(db.Numeric(12, 2), nullable=True)

    # Status
    verification_status = db.Column(
        db.String(20), nullable=False, default='PENDING', index=True
    )
    payment_status = db.Column(
        db.String(20), nullable=False, default='UNPAID', index=True
    )
    confidence_score = db.Column(db.Numeric(3, 2), nullable=True, default=0.0)

    # Metadata
    detected_date = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    verified_date = db.Column(db.DateTime(timezone=True), nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    payments = db.relationship('TaxPayment', backref='house', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('HouseDocument', backref='house', lazy='dynamic', cascade='all, delete-orphan')
    verification_history = db.relationship('VerificationHistory', backref='house', lazy='dynamic', cascade='all, delete-orphan')

    VALID_VERIFICATION_STATUSES = ('PENDING', 'AUTO_DETECTED', 'VERIFIED', 'DISPUTED', 'REJECTED')
    VALID_PAYMENT_STATUSES = ('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE', 'EXEMPT')

    def __repr__(self):
        return f'<House {self.immatriculation_number}>'
