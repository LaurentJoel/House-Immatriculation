"""
Tax Payment model.
"""
import uuid
from datetime import datetime, timezone

from app.core.extensions import db


class TaxPayment(db.Model):
    """Tax payment record for a house."""

    __tablename__ = 'tax_payments'

    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    house_id = db.Column(
        db.Integer,
        db.ForeignKey('houses.house_id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Payment details
    payment_year = db.Column(db.Integer, nullable=False)
    payment_period = db.Column(db.String(10), nullable=True)  # Q1, Q2, Q3, Q4, ANNUAL
    amount_due = db.Column(db.Numeric(12, 2), nullable=True)
    amount_paid = db.Column(db.Numeric(12, 2), nullable=False)
    penalty_amount = db.Column(db.Numeric(12, 2), nullable=True, default=0)

    # Payment method
    payment_method = db.Column(db.String(30), nullable=False)  # CASH, MOBILE_MONEY_MTN, MOBILE_MONEY_ORANGE, BANK
    transaction_reference = db.Column(db.String(100), nullable=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Status
    payment_status = db.Column(db.String(20), nullable=False, default='COMPLETED')
    payment_date = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Who processed
    collected_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    VALID_METHODS = ('CASH', 'MOBILE_MONEY_MTN', 'MOBILE_MONEY_ORANGE', 'BANK_TRANSFER')

    @staticmethod
    def generate_receipt_number() -> str:
        """Generate a unique receipt number."""
        return f"RCT-{uuid.uuid4().hex[:12].upper()}"

    def __repr__(self):
        return f'<TaxPayment {self.receipt_number} - {self.amount_paid} XAF>'
