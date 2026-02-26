"""
Tax Category model.
"""
from app.core.extensions import db


class TaxCategory(db.Model):
    """Tax category defining rates for different building types."""

    __tablename__ = 'tax_categories'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name_fr = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    base_rate_per_sqm = db.Column(db.Numeric(10, 2), nullable=False)
    description_fr = db.Column(db.Text, nullable=True)
    description_en = db.Column(db.Text, nullable=True)
    is_exempt = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    houses = db.relationship('House', backref='tax_category', lazy='dynamic')

    def __repr__(self):
        return f'<TaxCategory {self.code}>'
