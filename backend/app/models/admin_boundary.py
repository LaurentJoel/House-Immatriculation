"""
Administrative Boundary model.
"""
from geoalchemy2 import Geometry

from app.core.extensions import db


class AdminBoundary(db.Model):
    """Administrative boundary for regions, departments, and communes."""

    __tablename__ = 'admin_boundaries'

    boundary_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    boundary_type = db.Column(db.String(20), nullable=False, index=True)  # REGION, DEPARTMENT, COMMUNE
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    parent_code = db.Column(db.String(10), nullable=True)
    geom = db.Column(Geometry('MULTIPOLYGON', srid=4326), nullable=True)

    def __repr__(self):
        return f'<AdminBoundary {self.boundary_type}: {self.name} ({self.code})>'
