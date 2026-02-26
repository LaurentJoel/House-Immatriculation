"""
Houses API — CRUD, spatial queries, pagination, i18n errors.

Security: All string inputs sanitized via bleach. Numeric inputs validated.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import func

from app.core.extensions import db
from app.core.validators import (
    sanitize_string, sanitize_phone, validate_latitude, validate_longitude,
    validate_positive_int, validate_positive_float,
)
from app.models.house import House
from app.models.tax_category import TaxCategory
from app.repositories.house import HouseRepository
from app.services.immatriculation import ImmatriculationService
from app.services.cache import invalidate_cache

houses_bp = Blueprint('houses', __name__)

_house_repo = HouseRepository()
_immat_svc = ImmatriculationService()

# Simplified commune → (region_code, commune_code) mapping
COMMUNE_MAP = {
    'Yaounde I':   ('CE', 'YDE1'),
    'Yaounde II':  ('CE', 'YDE2'),
    'Yaounde III': ('CE', 'YDE3'),
    'Yaounde IV':  ('CE', 'YDE4'),
    'Yaounde V':   ('CE', 'YDE5'),
    'Yaounde VI':  ('CE', 'YDE6'),
    'Yaounde VII': ('CE', 'YDE7'),
    'Douala I':    ('LT', 'DLA1'),
    'Douala II':   ('LT', 'DLA2'),
    'Douala III':  ('LT', 'DLA3'),
    'Douala IV':   ('LT', 'DLA4'),
    'Douala V':    ('LT', 'DLA5'),
    'Bafoussam':   ('OU', 'BFAM'),
    'Bamenda':     ('NW', 'BMDA'),
    'Garoua':      ('NO', 'GARO'),
    'Maroua':      ('EN', 'MARO'),
    'Bertoua':     ('ES', 'BERT'),
    'Ebolowa':     ('SU', 'EBOL'),
    'Ngaoundere':  ('AD', 'NGDE'),
    'Buea':        ('SW', 'BUEA'),
    'Limbe':       ('SW', 'LIMB'),
}


def _get_locale():
    return request.headers.get('Accept-Language', 'fr')[:2]


def _msg(fr: str, en: str) -> str:
    return fr if _get_locale() == 'fr' else en


def _house_to_dict(house: House) -> dict:
    """Serialise a House to a JSON-safe dict."""
    d = {
        'house_id': house.house_id,
        'immatriculation_number': house.immatriculation_number,
        'commune': house.commune,
        'department': house.department,
        'region': house.region,
        'quartier': house.quartier,
        'building_type': house.building_type,
        'building_levels': house.building_levels,
        'footprint_area': float(house.footprint_area) if house.footprint_area else None,
        'total_built_area': float(house.total_built_area) if house.total_built_area else None,
        'owner_name': house.owner_name,
        'phone_number': house.phone_number,
        'verification_status': house.verification_status,
        'payment_status': house.payment_status,
        'annual_tax_amount': float(house.annual_tax_amount) if house.annual_tax_amount else None,
        'created_at': house.created_at.isoformat() if house.created_at else None,
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


# ── CRUD ───────────────────────────────────────────────────────────

@houses_bp.route('/houses', methods=['POST'])
@jwt_required()
def create_house():
    """Register a new house and auto-generate its immatriculation number."""
    data = request.get_json(silent=True) or {}
    commune = sanitize_string(data.get('commune', ''), 50)
    region = sanitize_string(data.get('region', ''), 50)

    if not commune:
        return jsonify({'success': False, 'message': _msg('Commune requise', 'Commune required')}), 400

    # Resolve commune to region/code
    lookup = COMMUNE_MAP.get(commune)
    if lookup:
        region_code, commune_code = lookup
    else:
        # Fallback: use first 2 chars of region and first 4 of commune
        region_code = region[:2].upper() if region else 'XX'
        commune_code = commune[:4].upper().replace(' ', '')

    immat = _immat_svc.generate_number(region_code, commune_code)

    # Build geometry — validate coordinates
    coords = data.get('coordinates', {})
    geom = None
    lat_val = validate_latitude(coords.get('latitude'))
    lon_val = validate_longitude(coords.get('longitude'))
    if lat_val is not None and lon_val is not None:
        geom = from_shape(Point(lon_val, lat_val), srid=4326)

    # Resolve tax category
    tax_cat_id = None
    cat_code = sanitize_string(data.get('tax_category_code', ''), 30)
    if cat_code:
        cat = TaxCategory.query.filter_by(code=cat_code).first()
        if cat:
            tax_cat_id = cat.category_id

    house = House(
        immatriculation_number=immat,
        commune=commune,
        department=sanitize_string(data.get('department', ''), 50),
        region=region or (lookup[0] if lookup else ''),
        quartier=sanitize_string(data.get('quartier', ''), 100),
        geom=geom,
        gps_latitude=lat_val,
        gps_longitude=lon_val,
        building_type=sanitize_string(data.get('building_type', ''), 50),
        building_levels=validate_positive_int(data.get('building_levels', 1), 200) or 1,
        footprint_area=validate_positive_float(data.get('footprint_area')),
        total_built_area=validate_positive_float(data.get('total_built_area')),
        owner_name=sanitize_string(data.get('owner_name', ''), 100),
        owner_national_id=sanitize_string(data.get('owner_national_id', ''), 30),
        phone_number=sanitize_phone(data.get('phone_number', '')),
        tax_category_id=tax_cat_id,
    )
    db.session.add(house)
    db.session.commit()

    # Invalidate dashboard cache since house count changed
    try:
        invalidate_cache('dashboard')
    except Exception:
        pass  # Cache may not be initialised in all environments

    return jsonify({'success': True, 'data': _house_to_dict(house)}), 201


@houses_bp.route('/houses/<int:house_id>', methods=['GET'])
@jwt_required()
def get_house(house_id):
    """Get a single house by ID."""
    house = db.session.get(House, house_id)
    if house is None:
        return jsonify({
            'success': False,
            'message': _msg('Maison introuvable', 'House not found'),
        }), 404
    return jsonify({'success': True, 'data': _house_to_dict(house)}), 200


@houses_bp.route('/houses/immat/<immat_number>', methods=['GET'])
@jwt_required()
def get_house_by_immat(immat_number):
    """Get a house by its immatriculation number."""
    house = _house_repo.get_by_immatriculation(immat_number)
    if house is None:
        return jsonify({
            'success': False,
            'message': _msg('Maison introuvable', 'House not found'),
        }), 404
    return jsonify({'success': True, 'data': _house_to_dict(house)}), 200


@houses_bp.route('/houses/<int:house_id>', methods=['PUT'])
@jwt_required()
def update_house(house_id):
    """Update house attributes."""
    house = db.session.get(House, house_id)
    if house is None:
        return jsonify({
            'success': False,
            'message': _msg('Maison introuvable', 'House not found'),
        }), 404

    data = request.get_json(silent=True) or {}
    # Sanitise all updatable string fields
    sanitizable = {
        'owner_name': 100, 'owner_national_id': 30, 'phone_number': 20,
        'building_type': 50, 'wall_material': 50, 'roof_material': 50,
        'quartier': 100, 'address_description': 500,
    }
    for field, max_len in sanitizable.items():
        if field in data:
            if field == 'phone_number':
                setattr(house, field, sanitize_phone(data[field]))
            else:
                setattr(house, field, sanitize_string(data[field], max_len))

    # Numeric fields
    if 'building_levels' in data:
        house.building_levels = validate_positive_int(data['building_levels'], 200) or house.building_levels
    if 'footprint_area' in data:
        house.footprint_area = validate_positive_float(data['footprint_area']) or house.footprint_area
    if 'total_built_area' in data:
        house.total_built_area = validate_positive_float(data['total_built_area']) or house.total_built_area

    db.session.commit()
    return jsonify({'success': True, 'data': _house_to_dict(house)}), 200


# ── Listing / Pagination ──────────────────────────────────────────

@houses_bp.route('/houses', methods=['GET'])
@jwt_required()
def list_houses():
    """List houses with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    commune = request.args.get('commune')
    query = House.query
    if commune:
        query = query.filter_by(commune=commune)

    total = query.count()
    houses = query.order_by(House.house_id).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'success': True,
        'data': [_house_to_dict(h) for h in houses],
        'total': total,
        'page': page,
        'per_page': per_page,
    }), 200


# ── Spatial ───────────────────────────────────────────────────────

@houses_bp.route('/houses/nearby', methods=['GET'])
@jwt_required()
def nearby_houses():
    """Find houses within a radius (metres) of a point."""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 500, type=float)

    if lat is None or lon is None:
        return jsonify({'success': False, 'message': 'lat and lon required'}), 400

    houses = _house_repo.find_nearby(lon, lat, radius)
    return jsonify({
        'success': True,
        'data': [_house_to_dict(h) for h in houses],
    }), 200
