"""
Tests for spatial model features (Step 2.3).
PostGIS queries: geometry creation, nearby search, boundary containment.
"""
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import func

from app.models import House, AdminBoundary


class TestHouseGeometry:
    """Test spatial geometry on House model."""

    def test_house_with_geometry(self, db_session):
        """Verify a house can be stored with a PostGIS POINT."""
        point = from_shape(Point(11.5167, 3.8667), srid=4326)  # Yaoundé
        house = House(
            immatriculation_number='CMR-CE-YDE1-0000003',
            geom=point,
            commune='Yaounde I',
            region='Centre',
        )
        db_session.add(house)
        db_session.commit()

        assert house.geom is not None
        # Reload from DB and verify geometry roundtrip
        loaded = db_session.get(House, house.house_id)
        shape = to_shape(loaded.geom)
        assert round(shape.x, 4) == 11.5167
        assert round(shape.y, 4) == 3.8667

    def test_spatial_query_nearby(self, db_session):
        """Test finding houses within a radius using ST_DWithin."""
        # Create houses at known locations in Yaoundé
        locations = [
            ('CMR-CE-YDE1-0001', Point(11.5167, 3.8667), 'Yaounde I'),   # reference
            ('CMR-CE-YDE1-0002', Point(11.5170, 3.8670), 'Yaounde I'),   # ~50m away
            ('CMR-CE-YDE1-0003', Point(11.6000, 3.9500), 'Yaounde VI'),  # ~15km away
        ]
        for immat, pt, commune in locations:
            house = House(
                immatriculation_number=immat,
                geom=from_shape(pt, srid=4326),
                commune=commune,
                region='Centre',
            )
            db_session.add(house)
        db_session.commit()

        # Query houses within 500m of the reference point
        ref_point = func.ST_SetSRID(func.ST_MakePoint(11.5167, 3.8667), 4326)
        nearby = House.query.filter(
            func.ST_DWithin(
                func.ST_Transform(House.geom, 32632),
                func.ST_Transform(ref_point, 32632),
                500,  # 500 metres
            )
        ).all()

        # The reference and the ~50m house should be found; the 15km one should not
        assert len(nearby) >= 2
        immat_numbers = {h.immatriculation_number for h in nearby}
        assert 'CMR-CE-YDE1-0001' in immat_numbers
        assert 'CMR-CE-YDE1-0002' in immat_numbers
        assert 'CMR-CE-YDE1-0003' not in immat_numbers
