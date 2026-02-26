"""
Tests for TaxService (Step 3.5).
"""
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models import House, TaxCategory
from app.services.tax import TaxService


def _make_category(db_session, code, rate, exempt=False):
    cat = TaxCategory(
        code=code,
        name_fr=code,
        name_en=code,
        base_rate_per_sqm=rate,
        is_exempt=exempt,
    )
    db_session.add(cat)
    db_session.commit()
    return cat


def _make_house(db_session, category, area=100, levels=1):
    h = House(
        immatriculation_number=f'CMR-CE-YDE1-{House.query.count() + 1:07d}',
        commune='Yaounde I',
        region='Centre',
        geom=from_shape(Point(11.5167, 3.8667), srid=4326),
        total_built_area=area,
        building_levels=levels,
        tax_category_id=category.category_id,
    )
    db_session.add(h)
    db_session.commit()
    return h


class TestTaxService:
    """Step 3.5: Tax calculation tests."""

    def test_calculate_residential_tax(self, db_session):
        svc = TaxService()
        cat = _make_category(db_session, 'RESIDENTIAL', rate=500)
        house = _make_house(db_session, cat, area=150, levels=2)
        tax = svc.calculate_annual_tax(house.house_id, 2026)
        assert tax > 0
        assert isinstance(tax, float)
        # 500 * 150 * 2 = 150000
        assert tax == 150000.0

    def test_commercial_higher_than_residential(self, db_session):
        svc = TaxService()
        res_cat = _make_category(db_session, 'RESIDENTIAL', rate=500)
        com_cat = _make_category(db_session, 'COMMERCIAL', rate=1200)
        res = _make_house(db_session, res_cat, area=100)
        com = _make_house(db_session, com_cat, area=100)
        tax_res = svc.calculate_annual_tax(res.house_id, 2026)
        tax_com = svc.calculate_annual_tax(com.house_id, 2026)
        assert tax_com > tax_res

    def test_government_exempt(self, db_session):
        svc = TaxService()
        gov_cat = _make_category(db_session, 'GOVERNMENT', rate=500, exempt=True)
        gov = _make_house(db_session, gov_cat, area=200)
        tax = svc.calculate_annual_tax(gov.house_id, 2026)
        assert tax == 0

    def test_penalty_calculation(self, db_session):
        svc = TaxService()
        penalty = svc.calculate_penalty(50000, months_late=3, rate=0.05)
        assert penalty == 7500  # 50000 * 0.05 * 3
