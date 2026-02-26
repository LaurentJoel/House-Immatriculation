"""
Reports API — cached dashboard stats and reference data.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.core.extensions import db
from app.models.house import House
from app.services.cache import cached

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports/dashboard', methods=['GET'])
@jwt_required()
@cached(ttl=300, prefix='dashboard')
def dashboard_stats():
    """Return aggregated dashboard statistics (cached)."""
    total_houses = db.session.query(func.count(House.house_id)).scalar()
    verified = db.session.query(func.count(House.house_id)).filter(
        House.verification_status == 'VERIFIED').scalar()
    paid = db.session.query(func.count(House.house_id)).filter(
        House.payment_status == 'PAID').scalar()
    partial = db.session.query(func.count(House.house_id)).filter(
        House.payment_status == 'PARTIAL').scalar()
    unpaid = db.session.query(func.count(House.house_id)).filter(
        House.payment_status == 'UNPAID').scalar()

    return {
        'success': True,
        'data': {
            'total_houses': total_houses,
            'verified': verified,
            'paid': paid,
            'partial': partial,
            'unpaid': unpaid,
        },
    }


@reports_bp.route('/admin/communes', methods=['GET'])
@jwt_required()
@cached(ttl=3600, prefix='ref')
def list_communes():
    """Return reference list of communes (cached)."""
    from app.api.routes.houses import COMMUNE_MAP
    communes = [
        {'name': name, 'region_code': codes[0], 'commune_code': codes[1]}
        for name, codes in COMMUNE_MAP.items()
    ]
    return {'success': True, 'data': communes}
