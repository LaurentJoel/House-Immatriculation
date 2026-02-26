"""
Database models package.
Import all models here so Alembic and SQLAlchemy can discover them.
"""
from app.models.user import User
from app.models.tax_category import TaxCategory
from app.models.house import House
from app.models.tax_payment import TaxPayment
from app.models.house_document import HouseDocument
from app.models.verification_history import VerificationHistory
from app.models.admin_boundary import AdminBoundary

__all__ = [
    'User',
    'TaxCategory',
    'House',
    'TaxPayment',
    'HouseDocument',
    'VerificationHistory',
    'AdminBoundary',
]
