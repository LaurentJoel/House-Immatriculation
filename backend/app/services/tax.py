"""
Tax calculation service.
"""
from decimal import Decimal
from typing import Optional

from app.core.extensions import db
from app.models.house import House
from app.models.tax_category import TaxCategory


class TaxService:
    """Service for calculating annual property taxes and penalties."""

    def calculate_annual_tax(self, house_id: int, year: int) -> float:
        """Calculate the annual tax for a house based on its category and area.

        Formula: base_rate_per_sqm * total_built_area * building_levels
        Government/exempt buildings return 0.
        """
        house = db.session.get(House, house_id)
        if house is None:
            raise ValueError(f'House {house_id} not found')

        category = house.tax_category
        if category is None:
            raise ValueError(f'House {house_id} has no tax category assigned')

        if category.is_exempt:
            return 0.0

        area = float(house.total_built_area or house.footprint_area or 0)
        levels = house.building_levels or 1
        rate = float(category.base_rate_per_sqm)

        return round(rate * area * levels, 2)

    @staticmethod
    def calculate_penalty(
        amount_due: float,
        months_late: int,
        rate: float = 0.05,
    ) -> float:
        """Calculate late-payment penalty.

        penalty = amount_due * rate * months_late
        """
        return round(amount_due * rate * months_late, 2)
