"""
Tests for HouseRepository (Step 3.2).
"""
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, TaxCategory
from app.repositories.house import HouseRepository


def _make_house(immat, commune='Yaounde I', region='Centre', lon=11.5167, lat=3.8667, **kw):
    """Helper to build a House with a geometry."""
    h = House(
        immatriculation_number=immat,
        commune=commune,
        region=region,
        geom=from_shape(Point(lon, lat), srid=4326),
        **kw,
    )
    return h


class TestHouseRepository:
    """Step 3.2: House repository tests."""

    def test_get_by_immatriculation(self, db_session):
        repo = HouseRepository()
        h = _make_house('CMR-CE-YDE1-0000010')
        db_session.add(h)
        db_session.commit()
        found = repo.get_by_immatriculation('CMR-CE-YDE1-0000010')
        assert found is not None
        assert found.house_id == h.house_id

    def test_find_by_commune(self, db_session):
        repo = HouseRepository()
        for i in range(10):
            db_session.add(_make_house(f'CMR-CE-YDE1-{i:07d}', commune='Yaounde I'))
        for i in range(5):
            db_session.add(_make_house(f'CMR-LT-DLA1-{i:07d}', commune='Douala I', region='Littoral', lon=9.7, lat=4.05))
        db_session.commit()
        houses = repo.find_by_commune('Yaounde I')
        assert len(houses) == 10

    def test_find_in_bounds(self, db_session):
        repo = HouseRepository()
        # houses inside the box
        db_session.add(_make_house('CMR-CE-YDE1-0000100', lon=11.52, lat=3.87))
        db_session.add(_make_house('CMR-CE-YDE1-0000101', lon=11.53, lat=3.88))
        # house outside the box
        db_session.add(_make_house('CMR-LT-DLA1-0000100', commune='Douala I', region='Littoral', lon=9.7, lat=4.05))
        db_session.commit()

        houses = repo.find_in_bounds(min_lat=3.85, min_lon=11.50, max_lat=3.90, max_lon=11.55)
        assert len(houses) == 2
        assert all(h.commune == 'Yaounde I' for h in houses)

    def test_count_by_status(self, db_session):
        repo = HouseRepository()
        db_session.add(_make_house('CMR-CE-YDE1-0000200', verification_status='VERIFIED'))
        db_session.add(_make_house('CMR-CE-YDE1-0000201', verification_status='VERIFIED'))
        db_session.add(_make_house('CMR-CE-YDE1-0000202', verification_status='PENDING'))
        db_session.commit()

        counts = repo.count_by_status()
        assert counts.get('VERIFIED') == 2
        assert counts.get('PENDING') == 1
