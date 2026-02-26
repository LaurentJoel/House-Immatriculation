"""
Tests for ImmatriculationService (Step 3.4).
"""
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House
from app.services.immatriculation import ImmatriculationService


def _create_house(db_session, immat):
    h = House(
        immatriculation_number=immat,
        commune='Yaounde I',
        region='Centre',
        geom=from_shape(Point(11.5167, 3.8667), srid=4326),
    )
    db_session.add(h)
    db_session.commit()
    return h


class TestImmatriculationService:
    """Step 3.4: Immatriculation number generation & validation."""

    def test_generate_immatriculation_number(self, db_session):
        svc = ImmatriculationService()
        num = svc.generate_number('CE', 'YDE1')
        assert num.startswith('CMR-CE-YDE1-')
        assert len(num) == 19  # CMR-CE-YDE1-0000001

    def test_sequential_numbers(self, db_session):
        svc = ImmatriculationService()
        num1 = svc.generate_number('CE', 'YDE1')
        _create_house(db_session, num1)
        num2 = svc.generate_number('CE', 'YDE1')
        seq1 = int(num1.split('-')[-1])
        seq2 = int(num2.split('-')[-1])
        assert seq2 == seq1 + 1

    def test_different_communes_independent(self, db_session):
        svc = ImmatriculationService()
        num_yde = svc.generate_number('CE', 'YDE1')
        num_dla = svc.generate_number('LT', 'DLA1')
        assert 'YDE1' in num_yde
        assert 'DLA1' in num_dla
        # Both should start at 1 (no existing records)
        assert num_yde.endswith('0000001')
        assert num_dla.endswith('0000001')

    def test_validate_immatriculation_format(self, db_session):
        svc = ImmatriculationService()
        assert svc.validate_format('CMR-CE-YDE1-0000001') is True
        assert svc.validate_format('INVALID') is False
        assert svc.validate_format('CMR-XX-YDE1-0000001') is False  # Invalid region
        assert svc.validate_format('CMR-LT-DLA1-0000099') is True
