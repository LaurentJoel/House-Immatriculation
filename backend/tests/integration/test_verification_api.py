"""
Integration tests for Verification API (Step 4.4).
"""
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, VerificationHistory


def _create_unverified_house(session, immat='CMR-CE-YDE1-0000001', status='PENDING',
                             lon=11.5167, lat=3.8667):
    h = House(
        immatriculation_number=immat,
        commune='Yaounde I',
        region='Centre',
        geom=from_shape(Point(lon, lat), srid=4326),
        verification_status=status,
    )
    session.add(h)
    session.commit()
    return h


def _create_unverified_houses(session, count=10):
    for i in range(count):
        _create_unverified_house(
            session,
            immat=f'CMR-CE-YDE1-{i:07d}',
            status='PENDING' if i % 2 == 0 else 'AUTO_DETECTED',
            lon=11.5167 + i * 0.0001,
            lat=3.8667 + i * 0.0001,
        )


class TestVerificationAPI:
    """Step 4.4: Field verification endpoints."""

    def test_get_nearby_unverified(self, client, agent_headers, db_session):
        _create_unverified_houses(db_session, count=10)
        response = client.get(
            '/api/v1/verification/nearby?lat=3.8667&lon=11.5167&radius=5000',
            headers=agent_headers,
        )
        assert response.status_code == 200
        assert len(response.json['data']) > 0
        for house in response.json['data']:
            assert house['verification_status'] in ['PENDING', 'AUTO_DETECTED']

    def test_verify_house(self, client, agent_headers, db_session):
        house = _create_unverified_house(db_session)
        response = client.post('/api/v1/verification/verify', headers=agent_headers, json={
            'immatriculation_number': house.immatriculation_number,
            'owner_name': 'Jean Verified',
            'phone_number': '+237699000000',
            'building_levels': 3,
            'building_type': 'villa',
            'gps_latitude': 3.8667,
            'gps_longitude': 11.5167,
        })
        assert response.status_code == 200
        # Check status updated
        updated = db_session.get(House, house.house_id)
        assert updated.verification_status == 'VERIFIED'
        assert float(updated.confidence_score) == 1.0

    def test_verification_history_created(self, client, agent_headers, db_session):
        house = _create_unverified_house(db_session)
        client.post('/api/v1/verification/verify', headers=agent_headers, json={
            'immatriculation_number': house.immatriculation_number,
            'owner_name': 'Test',
            'building_levels': 1,
            'building_type': 'house',
        })
        history = VerificationHistory.query.filter_by(house_id=house.house_id).all()
        assert len(history) == 1
        assert history[0].new_status == 'VERIFIED'
