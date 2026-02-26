"""
Verification History model - tracks field verification activities.
"""
from datetime import datetime, timezone

from app.core.extensions import db


class VerificationHistory(db.Model):
    """Track verification status changes for a house."""

    __tablename__ = 'verification_history'

    history_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_id = db.Column(
        db.Integer,
        db.ForeignKey('houses.house_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    verified_by = db.Column(
        db.Integer,
        db.ForeignKey('users.user_id'),
        nullable=False
    )
    previous_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    gps_latitude = db.Column(db.Numeric(10, 7), nullable=True)
    gps_longitude = db.Column(db.Numeric(10, 7), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f'<VerificationHistory house={self.house_id} {self.previous_status}->{self.new_status}>'
