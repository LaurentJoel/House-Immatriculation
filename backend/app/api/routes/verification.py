"""
Verification API — field agent verification endpoints.

Security: All inputs sanitized. GPS coords validated.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from geoalchemy2.shape import from_shape, to_shape
from geoalchemy2 import functions as gfunc
from shapely.geometry import Point
from sqlalchemy import func

from app.core.extensions import db
from app.core.validators import (
    sanitize_string, sanitize_phone, validate_latitude, validate_longitude,
    validate_positive_int,
)
from app.models.house import House
from app.models.verification_history import VerificationHistory

verification_bp = Blueprint('verification', __name__)


def _house_summary(house: House) -> dict:
    """Minimal serialisation for verification list."""
    d = {
        'house_id': house.house_id,
        'immatriculation_number': house.immatriculation_number,
        'commune': house.commune,
        'building_type': house.building_type,
        'building_levels': house.building_levels,
        'owner_name': house.owner_name,
        'verification_status': house.verification_status,
    }
    if house.geom is not None:
        try:
            shape = to_shape(house.geom)
            d['coordinates'] = {'latitude': shape.y, 'longitude': shape.x}
        except Exception:
            d['coordinates'] = None
    else:
        d['coordinates'] = None
    return d


@verification_bp.route('/verification/nearby', methods=['GET'])
@jwt_required()
def get_nearby_unverified():
    """Find unverified houses near a GPS point."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 1000, type=float)

    if lat is None or lon is None:
        return jsonify({'success': False, 'message': 'lat and lon required'}), 400

    ref_point = from_shape(Point(lon, lat), srid=4326)
    houses = (
        House.query
        .filter(House.verification_status.in_(['PENDING', 'AUTO_DETECTED']))
        .filter(
            gfunc.ST_DWithin(
                gfunc.ST_Transform(House.geom, 3857),
                gfunc.ST_Transform(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), 3857),
                radius,
            )
        )
        .all()
    )
    return jsonify({
        'success': True,
        'data': [_house_summary(h) for h in houses],
    }), 200


@verification_bp.route('/verification/verify', methods=['POST'])
@jwt_required()
def verify_house():
    """Mark a house as verified by a field agent."""
    data = request.get_json(silent=True) or {}
    immat = sanitize_string(data.get('immatriculation_number', ''), 25)
    if not immat:
        return jsonify({'success': False, 'message': 'immatriculation_number required'}), 400

    house = House.query.filter_by(immatriculation_number=immat).first()
    if house is None:
        return jsonify({'success': False, 'message': 'House not found'}), 404

    current_user_id = get_jwt_identity()
    previous_status = house.verification_status

    # Update house fields from field data — sanitized
    if 'owner_name' in data:
        house.owner_name = sanitize_string(data['owner_name'], 100)
    if 'phone_number' in data:
        house.phone_number = sanitize_phone(data['phone_number'])
    if 'building_levels' in data:
        house.building_levels = validate_positive_int(data['building_levels'], 200) or house.building_levels
    if 'building_type' in data:
        house.building_type = sanitize_string(data['building_type'], 50)

    house.verification_status = 'VERIFIED'
    house.confidence_score = 1.0
    house.verified_date = datetime.now(timezone.utc)
    house.verified_by = current_user_id

    # Update GPS if provided — validated
    gps_lat = validate_latitude(data.get('gps_latitude'))
    gps_lon = validate_longitude(data.get('gps_longitude'))
    if gps_lat and gps_lon:
        house.gps_latitude = gps_lat
        house.gps_longitude = gps_lon
        house.geom = from_shape(Point(gps_lon, gps_lat), srid=4326)

    # Record history
    history = VerificationHistory(
        house_id=house.house_id,
        verified_by=current_user_id,
        previous_status=previous_status,
        new_status='VERIFIED',
        gps_latitude=gps_lat,
        gps_longitude=gps_lon,
        notes=data.get('notes'),
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({'success': True, 'data': _house_summary(house)}), 200
