"""
House repository with spatial query support.
"""
from typing import Optional, List, Dict

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func

from app.core.extensions import db
from app.models.house import House
from app.repositories.base import BaseRepository


class HouseRepository(BaseRepository[House]):
    """Repository for House entities with spatial queries."""

    def __init__(self):
        super().__init__(House)

    def get_by_immatriculation(self, immat_number: str) -> Optional[House]:
        """Find a house by its immatriculation number."""
        return House.query.filter_by(immatriculation_number=immat_number).first()

    def find_by_commune(self, commune: str) -> List[House]:
        """Get all houses in a given commune."""
        return House.query.filter_by(commune=commune).all()

    def find_by_region(self, region: str) -> List[House]:
        """Get all houses in a given region."""
        return House.query.filter_by(region=region).all()

    def find_in_bounds(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
    ) -> List[House]:
        """Find houses whose geometry falls within a bounding box.

        Parameters use (lat, lon) but PostGIS uses (lon, lat).
        """
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        return House.query.filter(
            func.ST_Within(House.geom, envelope)
        ).all()

    def find_nearby(self, longitude: float, latitude: float, radius_m: float) -> List[House]:
        """Find houses within *radius_m* metres of a point."""
        ref = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        return House.query.filter(
            func.ST_DWithin(
                func.ST_Transform(House.geom, 32632),
                func.ST_Transform(ref, 32632),
                radius_m,
            )
        ).all()

    def count_by_status(self) -> Dict[str, int]:
        """Return a dict of verification_status → count."""
        rows = (
            db.session.query(House.verification_status, func.count(House.house_id))
            .group_by(House.verification_status)
            .all()
        )
        return {status: cnt for status, cnt in rows}
