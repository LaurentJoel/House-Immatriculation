"""
Integration tests for Houses API (Step 4.2).
"""
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, TaxCategory


def _seed_category(session, code='RESIDENTIAL', rate=500):
    cat = TaxCategory(code=code, name_fr=code, name_en=code, base_rate_per_sqm=rate)
    session.add(cat)
    session.commit()
    return cat


def _seed_house(session, immat='CMR-CE-YDE1-0000001', commune='Yaounde I',
                region='Centre', lon=11.5167, lat=3.8667, **kw):
    h = House(
        immatriculation_number=immat,
        commune=commune,
        region=region,
        geom=from_shape(Point(lon, lat), srid=4326),
        **kw,
    )
    session.add(h)
    session.commit()
    return h


class TestHousesAPI:
    """Step 4.2: Houses CRUD & spatial API tests."""

    def test_create_house(self, client, auth_headers, db_session):
        _seed_category(db_session, 'RESIDENTIAL')
        response = client.post('/api/v1/houses', headers=auth_headers, json={
            'commune': 'Yaounde I', 'department': 'Mfoundi', 'region': 'Centre',
            'building_type': 'villa', 'building_levels': 2,
            'footprint_area': 150.5, 'owner_name': 'Jean Dupont',
            'phone_number': '+237699123456', 'tax_category_code': 'RESIDENTIAL',
            'coordinates': {'latitude': 3.8667, 'longitude': 11.5167},
        })
        assert response.status_code == 201
        assert 'immatriculation_number' in response.json['data']
        assert response.json['data']['immatriculation_number'].startswith('CMR-CE-YDE1-')

    def test_get_house_by_id(self, client, auth_headers, db_session):
        house = _seed_house(db_session)
        response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
        assert response.status_code == 200
        assert response.json['data']['house_id'] == house.house_id

    def test_get_house_by_immatriculation(self, client, auth_headers, db_session):
        _seed_house(db_session, 'CMR-CE-YDE1-0000001')
        response = client.get('/api/v1/houses/immat/CMR-CE-YDE1-0000001', headers=auth_headers)
        assert response.status_code == 200
        assert response.json['data']['immatriculation_number'] == 'CMR-CE-YDE1-0000001'

    def test_update_house(self, client, auth_headers, db_session):
        house = _seed_house(db_session)
        response = client.put(f'/api/v1/houses/{house.house_id}', headers=auth_headers, json={
            'owner_name': 'Updated Name', 'building_levels': 3,
        })
        assert response.status_code == 200
        assert response.json['data']['owner_name'] == 'Updated Name'
        assert response.json['data']['building_levels'] == 3

    def test_list_houses_paginated(self, client, auth_headers, db_session):
        for i in range(25):
            _seed_house(db_session, immat=f'CMR-CE-YDE1-{i:07d}',
                        lon=11.5167 + i * 0.0001, lat=3.8667 + i * 0.0001)
        response = client.get('/api/v1/houses?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json['data']) == 10
        assert response.json['total'] == 25

    def test_get_nearby_houses(self, client, auth_headers, db_session):
        _seed_house(db_session, 'CMR-CE-YDE1-0000100', lon=11.5167, lat=3.8667)
        _seed_house(db_session, 'CMR-CE-YDE1-0000101', lon=11.5170, lat=3.8670)
        _seed_house(db_session, 'CMR-LT-DLA1-0000100', commune='Douala I',
                    region='Littoral', lon=9.7, lat=4.05)
        response = client.get(
            '/api/v1/houses/nearby?lat=3.8667&lon=11.5167&radius=500',
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json['data']) >= 2

    def test_house_not_found(self, client, auth_headers, db_session):
        response = client.get('/api/v1/houses/99999', headers=auth_headers)
        assert response.status_code == 404

    def test_bilingual_error_message_fr(self, client, auth_headers, db_session):
        headers = {**auth_headers, 'Accept-Language': 'fr'}
        response = client.get('/api/v1/houses/99999', headers=headers)
        assert response.status_code == 404
        assert 'introuvable' in response.json['message'].lower()

    def test_bilingual_error_message_en(self, client, auth_headers, db_session):
        headers = {**auth_headers, 'Accept-Language': 'en'}
        response = client.get('/api/v1/houses/99999', headers=headers)
        assert response.status_code == 404
        assert 'not found' in response.json['message'].lower()
