"""
Integration tests for Payments API (Step 4.3).
"""
from decimal import Decimal

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, TaxPayment


def _create_test_house(session, annual_tax=None, immat='CMR-CE-YDE1-0000001'):
    """Helper: create a house with optional annual_tax_amount."""
    h = House(
        immatriculation_number=immat,
        commune='Yaounde I',
        region='Centre',
        geom=from_shape(Point(11.5167, 3.8667), srid=4326),
        annual_tax_amount=annual_tax,
    )
    session.add(h)
    session.commit()
    return h


def _create_payments(session, house_id, count=5):
    """Helper: seed *count* payments for a house."""
    for i in range(count):
        p = TaxPayment(
            house_id=house_id,
            payment_year=2026,
            payment_period='Q1',
            amount_due=50000,
            amount_paid=10000,
            payment_method='CASH',
            receipt_number=TaxPayment.generate_receipt_number(),
        )
        session.add(p)
    session.commit()


class TestPaymentsAPI:
    """Step 4.3: Payments create, auto-status update, history."""

    def test_create_payment(self, client, auth_headers, db_session):
        house = _create_test_house(db_session)
        response = client.post('/api/v1/payments', headers=auth_headers, json={
            'house_id': house.house_id,
            'amount_paid': 25000,
            'payment_method': 'MOBILE_MONEY_MTN',
            'payment_year': 2026,
            'payment_period': 'Q1',
        })
        assert response.status_code == 201
        assert 'receipt_number' in response.json['data']

    def test_payment_updates_house_status(self, client, auth_headers, db_session):
        house = _create_test_house(db_session, annual_tax=50000)
        # Pay full amount
        client.post('/api/v1/payments', headers=auth_headers, json={
            'house_id': house.house_id,
            'amount_paid': 50000,
            'payment_method': 'CASH',
            'payment_year': 2026,
            'payment_period': 'ANNUAL',
        })
        # Check house status updated
        response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
        assert response.json['data']['payment_status'] == 'PAID'

    def test_partial_payment_status(self, client, auth_headers, db_session):
        house = _create_test_house(db_session, annual_tax=50000)
        client.post('/api/v1/payments', headers=auth_headers, json={
            'house_id': house.house_id,
            'amount_paid': 20000,
            'payment_method': 'CASH',
            'payment_year': 2026,
            'payment_period': 'Q1',
        })
        response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
        assert response.json['data']['payment_status'] == 'PARTIAL'

    def test_payment_history(self, client, auth_headers, db_session):
        house = _create_test_house(db_session)
        _create_payments(db_session, house.house_id, count=5)
        response = client.get(
            f'/api/v1/payments?house_id={house.house_id}', headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json['data']) == 5
