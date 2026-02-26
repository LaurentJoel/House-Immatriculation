"""
Immatriculation number generation and validation service.
"""
import re
from typing import Optional

from sqlalchemy import func

from app.core.extensions import db
from app.models.house import House


# Valid region codes for Cameroon (10 regions)
VALID_REGION_CODES = {
    'AD': 'Adamaoua',
    'CE': 'Centre',
    'EN': 'Extrême-Nord',
    'ES': 'Est',
    'LT': 'Littoral',
    'NO': 'Nord',
    'NW': 'Nord-Ouest',
    'OU': 'Ouest',
    'SU': 'Sud',
    'SW': 'Sud-Ouest',
}

# Pattern: CMR-<region>-<commune_code>-<7-digit sequence>
IMMAT_PATTERN = re.compile(
    r'^CMR-([A-Z]{2})-([A-Z0-9]{3,5})-(\d{7})$'
)


class ImmatriculationService:
    """Service for generating and validating immatriculation numbers."""

    def generate_number(self, region_code: str, commune_code: str) -> str:
        """Generate the next sequential immatriculation number.

        Format: CMR-<region>-<commune>-<0000001>
        """
        prefix = f'CMR-{region_code}-{commune_code}-'

        # Find the highest existing sequence for this commune
        max_num = (
            db.session.query(func.max(House.immatriculation_number))
            .filter(House.immatriculation_number.like(f'{prefix}%'))
            .scalar()
        )

        if max_num:
            seq = int(max_num.split('-')[-1]) + 1
        else:
            seq = 1

        return f'{prefix}{seq:07d}'

    @staticmethod
    def validate_format(immat_number: str) -> bool:
        """Check whether an immatriculation number matches the expected format."""
        match = IMMAT_PATTERN.match(immat_number)
        if not match:
            return False
        region_code = match.group(1)
        return region_code in VALID_REGION_CODES
