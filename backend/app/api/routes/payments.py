"""
Payments API — create payments, auto-update house status, history.

Security: Amount and method inputs validated. Payment method checked against whitelist.
"""
from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.core.extensions import db
from app.core.validators import sanitize_string, validate_positive_int, validate_positive_float
from app.models.house import House
from app.models.tax_payment import TaxPayment
from app.repositories.payment import PaymentRepository

payments_bp = Blueprint('payments', __name__)

_payment_repo = PaymentRepository()


def _payment_to_dict(payment: TaxPayment) -> dict:
    """Serialise a TaxPayment to a JSON-safe dict."""
    return {
        'payment_id': payment.payment_id,
        'house_id': payment.house_id,
        'payment_year': payment.payment_year,
        'payment_period': payment.payment_period,
        'amount_due': float(payment.amount_due) if payment.amount_due else None,
        'amount_paid': float(payment.amount_paid) if payment.amount_paid else None,
        'penalty_amount': float(payment.penalty_amount) if payment.penalty_amount else None,
        'payment_method': payment.payment_method,
        'receipt_number': payment.receipt_number,
        'payment_status': payment.payment_status,
        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
    }


def _update_house_payment_status(house: House, payment_year: int) -> None:
    """Recalculate and update house payment_status after a payment."""
    total_paid = _payment_repo.total_paid_for_year(house.house_id, payment_year)
    annual_tax = Decimal(str(house.annual_tax_amount or 0))

    if annual_tax <= 0:
        house.payment_status = 'PAID'
    elif total_paid >= annual_tax:
        house.payment_status = 'PAID'
    elif total_paid > 0:
        house.payment_status = 'PARTIAL'
    else:
        house.payment_status = 'UNPAID'
    db.session.commit()


@payments_bp.route('/payments', methods=['POST'])
@jwt_required()
def create_payment():
    """Record a new tax payment for a house."""
    data = request.get_json(silent=True) or {}
    house_id = validate_positive_int(data.get('house_id'))
    amount_paid = validate_positive_float(data.get('amount_paid'))
    payment_method = sanitize_string(data.get('payment_method', ''), 30)
    payment_year = validate_positive_int(data.get('payment_year'), 9999)

    if not all([house_id, amount_paid, payment_method, payment_year]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Whitelist payment methods
    if payment_method not in TaxPayment.VALID_METHODS:
        return jsonify({'success': False, 'message': 'Invalid payment method'}), 400

    house = db.session.get(House, house_id)
    if house is None:
        return jsonify({'success': False, 'message': 'House not found'}), 404

    payment = _payment_repo.create_payment(
        house_id=house_id,
        amount_due=float(house.annual_tax_amount or 0),
        amount_paid=float(amount_paid),
        payment_year=payment_year,
        payment_method=payment_method,
        payment_period=data.get('payment_period'),
    )

    # Auto-update house payment status
    _update_house_payment_status(house, payment_year)

    return jsonify({'success': True, 'data': _payment_to_dict(payment)}), 201


@payments_bp.route('/payments', methods=['GET'])
@jwt_required()
def list_payments():
    """List payments, optionally filtered by house_id."""
    house_id = request.args.get('house_id', type=int)
    if house_id:
        payments = _payment_repo.get_by_house(house_id)
    else:
        payments = TaxPayment.query.order_by(TaxPayment.payment_date.desc()).all()
    return jsonify({
        'success': True,
        'data': [_payment_to_dict(p) for p in payments],
    }), 200
