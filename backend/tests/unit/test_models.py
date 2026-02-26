"""
Tests for database setup and models (Steps 2.1 & 2.2).
"""
from datetime import date, datetime, timezone

from sqlalchemy import text, inspect

from app.models import User, House, TaxCategory, TaxPayment, HouseDocument, VerificationHistory, AdminBoundary


class TestDatabaseSetup:
    """Step 2.1: Database schema tests."""

    def test_all_tables_created(self, db_session, app):
        """Verify all model tables can be created."""
        from app.core.extensions import db as _db
        inspector = inspect(_db.engine)
        tables = inspector.get_table_names()
        assert 'users' in tables
        assert 'houses' in tables
        assert 'tax_payments' in tables
        assert 'tax_categories' in tables
        assert 'admin_boundaries' in tables
        assert 'house_documents' in tables
        assert 'verification_history' in tables

    def test_postgis_enabled(self, db_session):
        """Verify PostGIS extension is available."""
        result = db_session.execute(text("SELECT PostGIS_version()"))
        version = result.scalar()
        assert version is not None
        assert '3' in version


class TestUserModel:
    """Step 2.2: User model tests."""

    def test_user_creation(self, db_session):
        """Test creating a user."""
        user = User(username='agent1', email='agent@gov.cm', role='field_agent')
        user.set_password('secure123')
        db_session.add(user)
        db_session.commit()
        assert user.user_id is not None
        assert user.check_password('secure123') is True
        assert user.check_password('wrong') is False
        assert user.preferred_language == 'fr'
        assert user.is_active is True

    def test_user_default_language(self, db_session):
        """Test default language is French."""
        user = User(username='user_fr', email='fr@gov.cm')
        user.set_password('pass')
        db_session.add(user)
        db_session.commit()
        assert user.preferred_language == 'fr'

    def test_user_repr(self, db_session):
        """Test user string representation."""
        user = User(username='admin1', email='admin@gov.cm', role='super_admin')
        assert 'admin1' in repr(user)


class TestHouseModel:
    """Step 2.2: House model tests."""

    def test_house_creation(self, db_session):
        """Test creating a house with basic fields."""
        house = House(
            immatriculation_number='CMR-CE-YDE1-0000001',
            commune='Yaounde I',
            region='Centre',
            footprint_area=150.5,
            building_levels=2
        )
        db_session.add(house)
        db_session.commit()
        assert house.house_id is not None
        assert house.verification_status == 'PENDING'
        assert house.payment_status == 'UNPAID'

    def test_house_defaults(self, db_session):
        """Test house default values."""
        house = House(
            immatriculation_number='CMR-CE-YDE1-0000002',
            commune='Yaounde I',
            region='Centre'
        )
        db_session.add(house)
        db_session.commit()
        assert house.building_levels == 1
        assert house.verification_status == 'PENDING'
        assert house.payment_status == 'UNPAID'
        assert house.created_at is not None


class TestTaxCategoryModel:
    """Step 2.2: Tax category model tests."""

    def test_tax_category_creation(self, db_session):
        """Test creating a tax category."""
        cat = TaxCategory(
            code='RESIDENTIAL',
            name_fr='Residentiel',
            name_en='Residential',
            base_rate_per_sqm=500.00
        )
        db_session.add(cat)
        db_session.commit()
        assert cat.category_id is not None
        assert cat.is_exempt is False

    def test_exempt_category(self, db_session):
        """Test exempt tax category (government buildings)."""
        cat = TaxCategory(
            code='GOVERNMENT',
            name_fr='Gouvernement',
            name_en='Government',
            base_rate_per_sqm=0,
            is_exempt=True
        )
        db_session.add(cat)
        db_session.commit()
        assert cat.is_exempt is True


class TestPaymentModel:
    """Step 2.2: Tax payment model tests."""

    def test_payment_creation(self, db_session):
        """Test creating a payment."""
        house = House(
            immatriculation_number='CMR-CE-YDE1-0000003',
            commune='Yaounde I',
            region='Centre'
        )
        db_session.add(house)
        db_session.commit()

        payment = TaxPayment(
            house_id=house.house_id,
            payment_year=2026,
            amount_paid=50000,
            payment_method='MOBILE_MONEY_MTN',
            receipt_number=TaxPayment.generate_receipt_number()
        )
        db_session.add(payment)
        db_session.commit()
        assert payment.payment_id is not None
        assert payment.receipt_number.startswith('RCT-')

    def test_house_payment_relationship(self, db_session):
        """Test house-payment relationship."""
        house = House(
            immatriculation_number='CMR-CE-YDE1-0000004',
            commune='Yaounde I',
            region='Centre'
        )
        db_session.add(house)
        db_session.commit()

        for i in range(3):
            payment = TaxPayment(
                house_id=house.house_id,
                payment_year=2026,
                amount_paid=15000,
                payment_method='CASH',
                receipt_number=TaxPayment.generate_receipt_number()
            )
            db_session.add(payment)

        db_session.commit()
        assert house.payments.count() == 3


class TestVerificationHistoryModel:
    """Step 2.2: Verification history model tests."""

    def test_verification_created(self, db_session):
        """Test creating a verification record."""
        user = User(username='agent_v', email='agentv@gov.cm', role='field_agent')
        user.set_password('pass')
        db_session.add(user)

        house = House(
            immatriculation_number='CMR-CE-YDE1-0000005',
            commune='Yaounde I',
            region='Centre'
        )
        db_session.add(house)
        db_session.commit()

        history = VerificationHistory(
            house_id=house.house_id,
            verified_by=user.user_id,
            previous_status='PENDING',
            new_status='VERIFIED',
            notes='Field verification complete'
        )
        db_session.add(history)
        db_session.commit()
        assert history.history_id is not None
        assert history.new_status == 'VERIFIED'
