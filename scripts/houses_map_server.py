"""
Houses Map Server — DGI Cameroun
Serves /api/houses, /api/search, /api/stats, /api/airbnb,
       /api/tax-summary + the HTML map page.
Uses waitress (reliable on Windows).
Run:  python houses_map_server.py
"""
import json, os, threading
from decimal import Decimal
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

# ── Building tax filters: exclude non-building land use types ──
NON_BUILDING_TYPES = {
    'farmland', 'forest', 'meadow', 'orchard', 'quarry', 'plant_nursery',
    'military', 'railway', 'cemetery', 'village_green', 'greenfield',
    'brownfield', 'grass', 'farmyard', 'allotments', 'basin',
    'recreation_ground', 'landfill', 'reservoir',
}
MAX_BUILDING_AREA = 10000  # m² — real buildings rarely exceed this

def _is_taxable_building(building_type, area):
    """Return True if this entry is a real building eligible for tax."""
    if building_type and building_type.lower() in NON_BUILDING_TYPES:
        return False
    try:
        if float(area) >= MAX_BUILDING_AREA:
            return False
    except (ValueError, TypeError):
        return False
    return True

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}


def _decimal_default(obj):
    """JSON serializer for Decimal."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


# ── Cached Stats (COUNT DISTINCT on 3.9M takes ~30s) ────────────
_stats_cache = {
    "total_houses": 0, "with_immatriculation": 0, "unique_immatriculations": 0,
    "total_airbnb": 0, "with_commune": 0,
}

def _precompute_stats():
    """Run expensive stats query in background thread at startup."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Quick count first
        cur.execute("SELECT COUNT(*) FROM public.houses_immat;")
        _stats_cache["total_houses"] = cur.fetchone()[0]
        # Slower counts
        cur.execute("SELECT COUNT(col69), COUNT(DISTINCT col69) FROM public.houses_immat;")
        row = cur.fetchone()
        _stats_cache["with_immatriculation"] = row[0]
        _stats_cache["unique_immatriculations"] = row[1]
        # Houses with commune link
        cur.execute("SELECT COUNT(*) FROM public.houses_immat WHERE commune_gid IS NOT NULL;")
        _stats_cache["with_commune"] = cur.fetchone()[0]
        # Airbnb count
        cur.execute("SELECT COUNT(*) FROM immatriculation.airbnb_listings;")
        _stats_cache["total_airbnb"] = cur.fetchone()[0]
        conn.close()
        print(f"  [stats cached] total={_stats_cache['total_houses']:,}  immat={_stats_cache['with_immatriculation']:,}  unique={_stats_cache['unique_immatriculations']:,}  airbnb={_stats_cache['total_airbnb']}", flush=True)
    except Exception as e:
        print(f"  [stats error] {e}", flush=True)


@app.route("/test")
def test():
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return send_from_directory(SCRIPT_DIR, "houses_map.html")

@app.route("/api/stats")
def stats():
    """Return cached stats (precomputed at startup)."""
    return jsonify(_stats_cache)

@app.route("/api/houses")
def get_houses():
    """Return houses as GeoJSON in the given bounding box, with admin + tax info."""
    try:
        west = float(request.args.get("west", 8.0))
        south = float(request.args.get("south", 1.0))
        east = float(request.args.get("east", 16.0))
        north = float(request.args.get("north", 13.0))
        limit = min(int(request.args.get("limit", 5000)), 10000)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameters"}), 400
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT h.col0 AS id, h.col69 AS immatriculation, h.col31 AS building_type,
                   h.col67 AS area, h.col8 AS amenity, h.col12 AS name,
                   ST_AsGeoJSON(h.geom) AS geojson,
                   a.adm3_name1 AS commune, a.adm2_name1 AS departement, a.adm1_name AS region,
                   m.prix_m2_fcfa
            FROM public.houses_immat h
            LEFT JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
            LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
            LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
            WHERE h.geom IS NOT NULL
              AND h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
              AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
            ORDER BY CAST(COALESCE(h.col67, '0') AS float) DESC
            LIMIT %s;
        """, (west, south, east, north, limit))
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            # Compute estimated annual tax only for real buildings
            tax_est = None
            if row.get("area") and row.get("prix_m2_fcfa") and _is_taxable_building(row.get("building_type"), row.get("area")):
                try:
                    area_val = float(row["area"])
                    tax_est = round(area_val * float(row["prix_m2_fcfa"]) * 0.25)
                except (ValueError, TypeError):
                    pass
            props = {
                "id": row["id"], "immatriculation": row["immatriculation"],
                "building_type": row["building_type"], "area": row["area"],
                "amenity": row["amenity"], "name": row["name"],
                "commune": row["commune"], "departement": row["departement"],
                "region": row["region"], "prix_m2": row["prix_m2_fcfa"],
                "impot_estime": tax_est,
            }
            features.append({"type": "Feature", "geometry": geom, "properties": props})
        return jsonify({"type": "FeatureCollection", "features": features, "total_in_view": len(features)})
    finally:
        conn.close()

@app.route("/api/search")
def search_house():
    immat = request.args.get("immat", "").strip()
    if not immat:
        return jsonify({"error": "Missing immat parameter"}), 400
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT h.col0 AS id, h.col69 AS immatriculation, h.col31 AS building_type,
                   h.col67 AS area, h.col8 AS amenity, h.col12 AS name,
                   ST_AsGeoJSON(h.geom) AS geojson,
                   ST_X(ST_Centroid(h.geom)) AS center_lon, ST_Y(ST_Centroid(h.geom)) AS center_lat,
                   a.adm3_name1 AS commune, a.adm2_name1 AS departement, a.adm1_name AS region,
                   m.prix_m2_fcfa
            FROM public.houses_immat h
            LEFT JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
            LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
            LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
            WHERE h.col69 = %s AND h.geom IS NOT NULL
        """, (immat,))
        houses = cur.fetchall()
        if not houses:
            return jsonify({"error": "Not found", "found": False}), 404
        house_features = []
        for row in houses:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            tax_est = None
            if row.get("area") and row.get("prix_m2_fcfa") and _is_taxable_building(row.get("building_type"), row.get("area")):
                try:
                    tax_est = round(float(row["area"]) * float(row["prix_m2_fcfa"]) * 0.25)
                except (ValueError, TypeError):
                    pass
            house_features.append({"type": "Feature", "geometry": geom,
                "properties": {
                    "id": row["id"], "immatriculation": row["immatriculation"],
                    "building_type": row["building_type"], "area": row["area"],
                    "amenity": row["amenity"], "name": row["name"],
                    "commune": row["commune"], "departement": row["departement"],
                    "region": row["region"], "prix_m2": row["prix_m2_fcfa"],
                    "impot_estime": tax_est,
                }})
        cur.execute("""
            SELECT adm3_name1 AS adm3_name, adm2_name1 AS adm2_name, adm1_name, adm0_name,
                   adm3_pcode, adm2_pcode, area_sqkm, ST_AsGeoJSON(geom) AS geojson
            FROM public.cmr_admin3
            WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) LIMIT 1;
        """, (houses[0]["center_lon"], houses[0]["center_lat"]))
        admin = cur.fetchone()
        admin_feature = None
        admin_info = None
        if admin:
            admin_info = {
                "adm3_name": admin["adm3_name"], "adm2_name": admin["adm2_name"],
                "adm1_name": admin["adm1_name"], "adm0_name": admin["adm0_name"],
                "adm3_pcode": admin["adm3_pcode"], "adm2_pcode": admin["adm2_pcode"],
                "area_sqkm": str(admin["area_sqkm"]) if admin["area_sqkm"] else None,
            }
            admin_geom = json.loads(admin["geojson"]) if admin["geojson"] else None
            if admin_geom:
                admin_feature = {"type": "Feature", "geometry": admin_geom, "properties": admin_info}
        return jsonify({
            "found": True, "center": {"lat": houses[0]["center_lat"], "lon": houses[0]["center_lon"]},
            "houses": {"type": "FeatureCollection", "features": house_features},
            "admin_boundary": admin_feature, "admin_info": admin_info, "total_parts": len(house_features),
        })
    finally:
        conn.close()


@app.route("/api/airbnb")
def get_airbnb():
    """Return Airbnb listings with matched building polygon, admin & tax info."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        west = request.args.get("west")
        bbox_filter = ""
        params = ()
        if west is not None:
            try:
                west = float(west)
                south = float(request.args.get("south", 1.0))
                east = float(request.args.get("east", 16.0))
                north = float(request.args.get("north", 13.0))
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid bbox"}), 400
            bbox_filter = "AND ab.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
            params = (west, south, east, north)

        cur.execute(f"""
            SELECT ab.id, ab.ext_id, ab.title, ab.lat, ab.lon, ab.url,
                   ab.matched_building_id, ab.matched_immat, ab.match_distance_m,
                   ab.matched_commune, ab.matched_departement, ab.matched_region,
                   ST_AsGeoJSON(ab.geom) AS point_geojson,
                   h.col67 AS building_area, h.col31 AS building_type,
                   ST_AsGeoJSON(h.geom) AS building_geojson,
                   m.prix_m2_fcfa
            FROM immatriculation.airbnb_listings ab
            LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
            LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
            LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
            LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
            WHERE ab.geom IS NOT NULL {bbox_filter}
        """, params)
        rows = cur.fetchall()
        features = []
        for row in rows:
            # Use building polygon if available, otherwise point
            bldg_geom = json.loads(row["building_geojson"]) if row["building_geojson"] else None
            point_geom = json.loads(row["point_geojson"]) if row["point_geojson"] else None
            geom = bldg_geom or point_geom
            if not geom:
                continue

            # Compute tax estimate (Airbnb buildings are always taxable)
            tax_est = None
            if row.get("building_area") and row.get("prix_m2_fcfa"):
                try:
                    tax_est = round(float(row["building_area"]) * float(row["prix_m2_fcfa"]) * 0.25)
                except (ValueError, TypeError):
                    pass

            props = {
                "id": row["id"], "ext_id": row["ext_id"], "title": row["title"],
                "lat": row["lat"], "lon": row["lon"], "url": row["url"],
                "matched_building_id": row["matched_building_id"],
                "matched_immat": row["matched_immat"],
                "match_distance_m": float(row["match_distance_m"]) if row["match_distance_m"] else None,
                "matched_commune": row["matched_commune"],
                "matched_departement": row["matched_departement"],
                "matched_region": row["matched_region"],
                "building_area": row["building_area"],
                "building_type": row["building_type"] or "residential",
                "prix_m2": float(row["prix_m2_fcfa"]) if row["prix_m2_fcfa"] else None,
                "impot_estime": tax_est,
                "has_building_polygon": bldg_geom is not None,
            }
            features.append({"type": "Feature", "geometry": geom, "properties": props})
        return jsonify({"type": "FeatureCollection", "features": features, "count": len(features)})
    finally:
        conn.close()


@app.route("/api/admin-list")
def admin_list():
    """Return lists of regions, departments, communes for search dropdowns."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        # Regions
        cur.execute("SELECT DISTINCT adm1_name FROM cmr_admin3 WHERE adm1_name IS NOT NULL ORDER BY adm1_name")
        regions = [r[0] for r in cur.fetchall()]
        # Departments
        cur.execute("SELECT DISTINCT adm2_name1, adm1_name FROM cmr_admin3 WHERE adm2_name1 IS NOT NULL ORDER BY adm2_name1")
        departments = [{"name": r[0], "region": r[1]} for r in cur.fetchall()]
        # Communes
        cur.execute("SELECT DISTINCT adm3_name1, adm2_name1, adm1_name FROM cmr_admin3 WHERE adm3_name1 IS NOT NULL ORDER BY adm3_name1")
        communes = [{"name": r[0], "department": r[1], "region": r[2]} for r in cur.fetchall()]
        return jsonify({"regions": regions, "departments": departments, "communes": communes})
    finally:
        conn.close()


@app.route("/api/admin-browse")
def admin_browse():
    """Search houses inside a given admin area (region, department, or commune). Fly-to + return houses."""
    region = request.args.get("region", "").strip()
    department = request.args.get("department", "").strip()
    commune = request.args.get("commune", "").strip()
    limit = min(int(request.args.get("limit", 5000)), 10000)

    if not region and not department and not commune:
        return jsonify({"error": "Provide region, department, or commune"}), 400

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get admin boundary
        if commune:
            cur.execute("""
                SELECT gid, adm3_name1 AS name, adm2_name1 AS dept, adm1_name AS region,
                       ST_AsGeoJSON(geom) AS geojson,
                       ST_X(ST_Centroid(geom)) AS center_lon, ST_Y(ST_Centroid(geom)) AS center_lat,
                       ST_XMin(geom) AS west, ST_YMin(geom) AS south, ST_XMax(geom) AS east, ST_YMax(geom) AS north
                FROM cmr_admin3 WHERE lower(adm3_name1) = lower(%s)
                LIMIT 1
            """, (commune,))
        elif department:
            cur.execute("""
                SELECT min(gid) AS gid, adm2_name1 AS name, adm1_name AS region,
                       ST_AsGeoJSON(ST_Union(geom)) AS geojson,
                       ST_X(ST_Centroid(ST_Union(geom))) AS center_lon,
                       ST_Y(ST_Centroid(ST_Union(geom))) AS center_lat,
                       ST_XMin(ST_Union(geom)) AS west, ST_YMin(ST_Union(geom)) AS south,
                       ST_XMax(ST_Union(geom)) AS east, ST_YMax(ST_Union(geom)) AS north
                FROM cmr_admin3 WHERE lower(adm2_name1) = lower(%s)
                GROUP BY adm2_name1, adm1_name
                LIMIT 1
            """, (department,))
        else:
            cur.execute("""
                SELECT min(gid) AS gid, adm1_name AS name,
                       ST_AsGeoJSON(ST_Union(geom)) AS geojson,
                       ST_X(ST_Centroid(ST_Union(geom))) AS center_lon,
                       ST_Y(ST_Centroid(ST_Union(geom))) AS center_lat,
                       ST_XMin(ST_Union(geom)) AS west, ST_YMin(ST_Union(geom)) AS south,
                       ST_XMax(ST_Union(geom)) AS east, ST_YMax(ST_Union(geom)) AS north
                FROM cmr_admin3 WHERE lower(adm1_name) = lower(%s)
                GROUP BY adm1_name
                LIMIT 1
            """, (region,))

        admin_row = cur.fetchone()
        if not admin_row:
            return jsonify({"error": "Admin area not found", "found": False}), 404

        admin_geom = json.loads(admin_row["geojson"]) if admin_row["geojson"] else None
        admin_feature = None
        if admin_geom:
            admin_feature = {"type": "Feature", "geometry": admin_geom, "properties": {
                "name": admin_row["name"],
                "region": admin_row.get("region", admin_row["name"]),
                "dept": admin_row.get("dept"),
            }}

        # Get houses inside bounding box of admin area
        cur.execute("""
            SELECT h.col0 AS id, h.col69 AS immatriculation, h.col31 AS building_type,
                   h.col67 AS area, h.col8 AS amenity, h.col12 AS name,
                   ST_AsGeoJSON(h.geom) AS geojson,
                   a.adm3_name1 AS commune, a.adm2_name1 AS departement, a.adm1_name AS region,
                   m.prix_m2_fcfa
            FROM public.houses_immat h
            LEFT JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
            LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
            LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
            WHERE h.geom IS NOT NULL
              AND h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
              AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
            ORDER BY CAST(COALESCE(h.col67, '0') AS float) DESC
            LIMIT %s;
        """, (admin_row["west"], admin_row["south"], admin_row["east"], admin_row["north"], limit))
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            tax_est = None
            if row.get("area") and row.get("prix_m2_fcfa") and _is_taxable_building(row.get("building_type"), row.get("area")):
                try:
                    tax_est = round(float(row["area"]) * float(row["prix_m2_fcfa"]) * 0.25)
                except (ValueError, TypeError):
                    pass
            props = {
                "id": row["id"], "immatriculation": row["immatriculation"],
                "building_type": row["building_type"], "area": row["area"],
                "amenity": row["amenity"], "name": row["name"],
                "commune": row["commune"], "departement": row["departement"],
                "region": row["region"], "prix_m2": row["prix_m2_fcfa"],
                "impot_estime": tax_est,
            }
            features.append({"type": "Feature", "geometry": geom, "properties": props})

        # Count total in area
        count_where = ""
        if commune:
            count_where = "commune_gid IN (SELECT gid FROM cmr_admin3 WHERE lower(adm3_name1) = lower(%s))"
            count_param = (commune,)
        elif department:
            count_where = "commune_gid IN (SELECT gid FROM cmr_admin3 WHERE lower(adm2_name1) = lower(%s))"
            count_param = (department,)
        else:
            count_where = "commune_gid IN (SELECT gid FROM cmr_admin3 WHERE lower(adm1_name) = lower(%s))"
            count_param = (region,)
        cur.execute(f"SELECT COUNT(*) FROM houses_immat WHERE {count_where}", count_param)
        total_in_area = cur.fetchone()["count"]

        return jsonify({
            "found": True,
            "center": {"lat": float(admin_row["center_lat"]), "lon": float(admin_row["center_lon"])},
            "bbox": {"west": float(admin_row["west"]), "south": float(admin_row["south"]),
                     "east": float(admin_row["east"]), "north": float(admin_row["north"])},
            "admin_boundary": admin_feature,
            "houses": {"type": "FeatureCollection", "features": features},
            "total_in_area": total_in_area,
            "total_returned": len(features),
        })
    finally:
        conn.close()


@app.route("/api/tax-summary")
def tax_summary():
    """Return precomputed tax summaries (region or commune level)."""
    level = request.args.get("level", "regions")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if level == "communes":
            cur.execute("""
                SELECT name, dept_name, region_name, prix_m2_fcfa,
                       nb_batiments, surface_totale_m2, impot_estime_fcfa,
                       nb_airbnb, nb_airbnb_matched
                FROM immatriculation.tax_summary_communes
                ORDER BY impot_estime_fcfa DESC LIMIT 50
            """)
        else:
            cur.execute("""
                SELECT name, name_en, nb_batiments, surface_totale_m2,
                       impot_estime_fcfa, prix_mercurial_moyen, nb_airbnb
                FROM immatriculation.tax_summary_regions
                ORDER BY impot_estime_fcfa DESC
            """)
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({k: (float(v) if isinstance(v, Decimal) else v)
                           for k, v in row.items()})
        return jsonify({"level": level, "data": result})
    finally:
        conn.close()


# ── Choropleth GeoJSON Endpoints (admin regions/departments/communes) ──

@app.route("/api/admin/regions")
def admin_regions_geojson():
    """GeoJSON of all regions with geometry + tax stats for choropleth."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT r.name, r.name_en,
                   COALESCE(r.nb_batiments, 0) AS nb_batiments,
                   COALESCE(r.surface_totale_m2, 0) AS surface_totale_m2,
                   COALESCE(r.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                   COALESCE(r.prix_mercurial_moyen, 0) AS prix_mercurial_moyen,
                   COALESCE(r.nb_airbnb, 0) AS nb_airbnb,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(g.geom, 0.01)) AS geojson
            FROM immatriculation.tax_summary_regions r
            JOIN (
                SELECT adm1_name, ST_Union(geom) AS geom
                FROM public.cmr_admin3
                GROUP BY adm1_name
            ) g ON g.adm1_name = r.name
            ORDER BY r.impot_estime_fcfa DESC
        """)
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "name": row["name"],
                    "name_en": row["name_en"],
                    "nb_batiments": int(row["nb_batiments"]),
                    "surface_totale_m2": float(row["surface_totale_m2"]),
                    "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                    "prix_mercurial_moyen": float(row["prix_mercurial_moyen"]),
                    "prix_mercurial": float(row["prix_mercurial_moyen"]),
                    "nb_airbnb": int(row["nb_airbnb"]),
                }
            })
        return app.response_class(
            json.dumps({"type": "FeatureCollection", "features": features},
                       default=_decimal_default),
            mimetype='application/json'
        )
    finally:
        conn.close()


@app.route("/api/admin/departments")
def admin_departments_geojson():
    """GeoJSON of departments in a region with aggregated tax stats."""
    region = request.args.get("region", "").strip()
    if not region:
        return jsonify({"error": "Missing region parameter"}), 400
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.adm2_name1 AS name, a.adm1_name AS region_name,
                   ST_AsGeoJSON(ST_SimplifyPreserveTopology(
                       ST_Union(a.geom), 0.005)) AS geojson,
                   COALESCE(SUM(tc.nb_batiments), 0)::bigint AS nb_batiments,
                   COALESCE(SUM(tc.surface_totale_m2), 0) AS surface_totale_m2,
                   COALESCE(SUM(tc.impot_estime_fcfa), 0) AS impot_estime_fcfa,
                   CASE WHEN COUNT(tc.prix_m2_fcfa)
                            FILTER (WHERE tc.prix_m2_fcfa > 0) > 0
                        THEN AVG(tc.prix_m2_fcfa)
                            FILTER (WHERE tc.prix_m2_fcfa > 0)
                        ELSE 0 END AS prix_mercurial,
                   COALESCE(SUM(tc.nb_airbnb), 0)::bigint AS nb_airbnb
            FROM public.cmr_admin3 a
            LEFT JOIN immatriculation.tax_summary_communes tc
                ON tc.name = a.adm3_name1 AND tc.dept_name = a.adm2_name1
            WHERE a.adm1_name = %s
            GROUP BY a.adm2_name1, a.adm1_name
            ORDER BY SUM(tc.impot_estime_fcfa) DESC NULLS LAST
        """, (region,))
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "name": row["name"],
                    "region_name": row["region_name"],
                    "nb_batiments": int(row["nb_batiments"]),
                    "surface_totale_m2": float(row["surface_totale_m2"]),
                    "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                    "prix_mercurial": float(row["prix_mercurial"]),
                    "nb_airbnb": int(row["nb_airbnb"]),
                }
            })
        return app.response_class(
            json.dumps({"type": "FeatureCollection", "features": features},
                       default=_decimal_default),
            mimetype='application/json'
        )
    finally:
        conn.close()


@app.route("/api/admin/communes")
def admin_communes_geojson():
    """GeoJSON of communes in a department with tax stats."""
    department = request.args.get("department", "").strip()
    if not department:
        return jsonify({"error": "Missing department parameter"}), 400
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT a.gid, a.adm3_name1 AS name, a.adm2_name1 AS dept_name,
                   a.adm1_name AS region_name, a.adm3_pcode AS pcode,
                   ST_AsGeoJSON(a.geom) AS geojson,
                   COALESCE(tc.nb_batiments, 0) AS nb_batiments,
                   COALESCE(tc.surface_totale_m2, 0) AS surface_totale_m2,
                   COALESCE(tc.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                   COALESCE(tc.prix_m2_fcfa, 0) AS prix_mercurial,
                   COALESCE(tc.nb_airbnb, 0) AS nb_airbnb
            FROM public.cmr_admin3 a
            LEFT JOIN immatriculation.tax_summary_communes tc
                ON tc.name = a.adm3_name1 AND tc.dept_name = a.adm2_name1
            WHERE a.adm2_name1 = %s
            ORDER BY tc.impot_estime_fcfa DESC NULLS LAST
        """, (department,))
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "gid": row["gid"],
                    "name": row["name"],
                    "dept_name": row["dept_name"],
                    "region_name": row["region_name"],
                    "pcode": row["pcode"],
                    "nb_batiments": int(row["nb_batiments"]),
                    "surface_totale_m2": float(row["surface_totale_m2"]),
                    "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                    "prix_mercurial": float(row["prix_mercurial"]),
                    "nb_airbnb": int(row["nb_airbnb"]),
                }
            })
        return app.response_class(
            json.dumps({"type": "FeatureCollection", "features": features},
                       default=_decimal_default),
            mimetype='application/json'
        )
    finally:
        conn.close()


@app.route("/api/tax/summary")
def tax_national_summary():
    """National aggregate tax stats from precomputed tables."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT COALESCE(SUM(nb_batiments), 0) AS total_batiments,
                   COALESCE(SUM(surface_totale_m2), 0) AS surface_totale_m2,
                   COALESCE(SUM(impot_estime_fcfa), 0) AS impot_estime_total,
                   COALESCE(SUM(nb_airbnb), 0) AS airbnb_total
            FROM immatriculation.tax_summary_regions
        """)
        row = cur.fetchone()
        return jsonify({
            "total_batiments": int(row["total_batiments"]),
            "surface_totale_m2": float(row["surface_totale_m2"]),
            "impot_estime_total": float(row["impot_estime_total"]),
            "airbnb_total": int(row["airbnb_total"]),
        })
    finally:
        conn.close()


@app.route("/api/buildings")
def get_buildings():
    """Return buildings as GeoJSON — by commune_gid or bounding box."""
    commune_gid = request.args.get("commune_gid")
    try:
        limit = min(int(request.args.get("limit", 5000)), 10000)
    except (ValueError, TypeError):
        limit = 5000

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if commune_gid:
            try:
                commune_gid = int(commune_gid)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid commune_gid"}), 400
            cur.execute("""
                SELECT h.col0 AS id, h.col69 AS immatriculation,
                       h.col31 AS building_type, h.col67 AS area_m2,
                       ST_AsGeoJSON(h.geom) AS geojson, m.prix_m2_fcfa
                FROM public.houses_immat h
                LEFT JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
                LEFT JOIN immatriculation.commune_name_alias ca
                    ON a.adm3_name1 = ca.admin_name
                LEFT JOIN immatriculation.mercuriale_lookup m
                    ON ca.mercuriale_name = m.commune_name
                WHERE h.commune_gid = %s AND h.geom IS NOT NULL
                ORDER BY CAST(COALESCE(h.col67, '0') AS float) DESC
                LIMIT %s
            """, (commune_gid, limit))
        else:
            try:
                west = float(request.args.get("west", 8.0))
                south = float(request.args.get("south", 1.0))
                east = float(request.args.get("east", 16.0))
                north = float(request.args.get("north", 13.0))
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid bbox parameters"}), 400
            cur.execute("""
                SELECT h.col0 AS id, h.col69 AS immatriculation,
                       h.col31 AS building_type, h.col67 AS area_m2,
                       ST_AsGeoJSON(h.geom) AS geojson, m.prix_m2_fcfa
                FROM public.houses_immat h
                LEFT JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
                LEFT JOIN immatriculation.commune_name_alias ca
                    ON a.adm3_name1 = ca.admin_name
                LEFT JOIN immatriculation.mercuriale_lookup m
                    ON ca.mercuriale_name = m.commune_name
                WHERE h.geom IS NOT NULL
                  AND h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                ORDER BY CAST(COALESCE(h.col67, '0') AS float) DESC
                LIMIT %s
            """, (west, south, east, north, limit))

        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            area = row.get("area_m2")
            prix = row.get("prix_m2_fcfa")
            tax = None
            if area and prix and _is_taxable_building(row.get("building_type"), area):
                try:
                    tax = round(float(area) * float(prix) * 0.25)
                except (ValueError, TypeError):
                    pass
            try:
                area_num = round(float(area), 1) if area else 0
            except (ValueError, TypeError):
                area_num = 0
            features.append({"type": "Feature", "geometry": geom,
                "properties": {
                    "immatriculation": row["immatriculation"],
                    "area_m2": area_num,
                    "prix_m2_fcfa": float(prix) if prix else None,
                    "impot_annuel": tax,
                }})
        return app.response_class(
            json.dumps({"type": "FeatureCollection", "features": features,
                        "count": len(features)}, default=_decimal_default),
            mimetype='application/json'
        )
    finally:
        conn.close()


if __name__ == "__main__":
    PORT = 5558
    print(f"DGI Cameroun Server starting on http://localhost:{PORT}", flush=True)
    print(f"  Dashboard:  http://localhost:{PORT}/", flush=True)
    print(f"  API: /api/stats, /api/houses, /api/search, /api/airbnb, /api/tax-summary", flush=True)
    print(f"  Choropleth: /api/admin/regions, /api/admin/departments, /api/admin/communes", flush=True)
    print(f"  Data: /api/tax/summary, /api/buildings", flush=True)

    # Pre-compute stats in background (takes ~30s for COUNT DISTINCT)
    threading.Thread(target=_precompute_stats, daemon=True).start()

    from waitress import serve
    serve(app, host="127.0.0.1", port=PORT, threads=6)
