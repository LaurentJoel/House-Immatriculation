"""
Tests for PaymentRepository (Step 3.3).
"""
from decimal import Decimal

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, TaxPayment
from app.repositories.payment import PaymentRepository


def _make_house(db_session, immat='CMR-CE-YDE1-0000001'):
    h = House(
        immatriculation_number=immat,
        commune='Yaounde I',
        region='Centre',
        geom=from_shape(Point(11.5167, 3.8667), srid=4326),
    )
    db_session.add(h)
    db_session.commit()
    return h


class TestPaymentRepository:
    """Step 3.3: Payment repository tests."""

    def test_create_payment(self, db_session):
        repo = PaymentRepository()
        house = _make_house(db_session)
        payment = repo.create_payment(
            house_id=house.house_id,
            amount_due=50000,
            amount_paid=50000,
            payment_year=2026,
            payment_method='MOBILE_MONEY_MTN',
        )
        assert payment.payment_id is not None
        assert payment.receipt_number is not None
        assert payment.receipt_number.startswith('RCT-')

    def test_get_payments_by_house(self, db_session):
        repo = PaymentRepository()
        house = _make_house(db_session)
        for i in range(3):
            repo.create_payment(
                house_id=house.house_id,
                amount_due=10000, amount_paid=10000,
                payment_year=2026,
                payment_method='CASH',
            )
        payments = repo.get_by_house(house.house_id)
        assert len(payments) == 3

    def test_get_total_paid_by_year(self, db_session):
        repo = PaymentRepository()
        house = _make_house(db_session)
        amounts = [20000, 15000, 15000]
        for a in amounts:
            repo.create_payment(
                house_id=house.house_id,
                amount_due=a, amount_paid=a,
                payment_year=2026,
                payment_method='CASH',
            )
        total = repo.total_paid_for_year(house.house_id, 2026)
        assert total == Decimal('50000')
