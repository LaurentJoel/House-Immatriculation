"""
House Document model (photos, certificates, etc.)
"""
from datetime import datetime, timezone

from app.core.extensions import db


class HouseDocument(db.Model):
    """Document attached to a house (photos, certificates, etc.)."""

    __tablename__ = 'house_documents'

    document_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_id = db.Column(
        db.Integer,
        db.ForeignKey('houses.house_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    document_type = db.Column(db.String(30), nullable=False)  # PHOTO, CERTIFICATE, TITLE_DEED, OTHER
    file_path = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f'<HouseDocument {self.document_type}: {self.file_name}>'
