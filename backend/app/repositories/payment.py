"""
Payment repository.
"""
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import func

from app.core.extensions import db
from app.models.tax_payment import TaxPayment
from app.models.house import House
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[TaxPayment]):
    """Repository for TaxPayment entities."""

    def __init__(self):
        super().__init__(TaxPayment)

    def create_payment(
        self,
        house_id: int,
        amount_due: float,
        amount_paid: float,
        payment_year: int,
        payment_method: str,
        **kwargs,
    ) -> TaxPayment:
        """Create and persist a new payment with auto-generated receipt."""
        payment = TaxPayment(
            house_id=house_id,
            amount_due=amount_due,
            amount_paid=amount_paid,
            payment_year=payment_year,
            payment_method=payment_method,
            receipt_number=TaxPayment.generate_receipt_number(),
            **kwargs,
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    def get_by_house(self, house_id: int) -> List[TaxPayment]:
        """Get all payments for a specific house."""
        return TaxPayment.query.filter_by(house_id=house_id).order_by(
            TaxPayment.payment_date.desc()
        ).all()

    def get_by_receipt(self, receipt_number: str) -> Optional[TaxPayment]:
        """Find a payment by its receipt number."""
        return TaxPayment.query.filter_by(receipt_number=receipt_number).first()

    def total_paid_for_year(self, house_id: int, year: int) -> Decimal:
        """Sum all payments for a house in a given year."""
        result = (
            db.session.query(func.coalesce(func.sum(TaxPayment.amount_paid), 0))
            .filter(TaxPayment.house_id == house_id, TaxPayment.payment_year == year)
            .scalar()
        )
        return Decimal(str(result))
