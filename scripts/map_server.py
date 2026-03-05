"""
Flask API for the DGI Cameroun Dashboard.
Serves house data, admin boundaries, tax aggregations, and Airbnb data.
Run with:  python map_server.py
"""
import json, os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras

# Ensure working directory is the scripts folder (important for static files)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, static_folder='.')
CORS(app)

# ── Database config ──────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

# ── French accent corrections ────────────────────────────────────
DEPT_ACCENT_FIX = {
    "B??nou??": "Bénoué", "Diamar??": "Diamaré", "Dj??rem": "Djérem",
    "Faro-et-D??o": "Faro-et-Déo", "Leki??": "Lékié",
    "Lom-et-Dj??rem": "Lom-et-Djérem", "Mb??r??": "Mbéré", "Nd??": "Ndé",
    "Nyong-et-Kell??": "Nyong-et-Kellé", "Oc??an": "Océan",
    "Vall??e-du-Ntem": "Vallée-du-Ntem",
}

COMMUNE_ACCENT_FIX = {
    "Bangangte": "Bangangté", "Batie": "Batié", "Doume": "Doumé",
    "Eseka": "Eséka", "Fokoue": "Fokoué", "Galim-Tignere": "Galim-Tignère",
    "Guere": "Guéré", "Kaele": "Kaélé", "Kekem": "Kékem", "Kette": "Ketté",
    "Lomie": "Lomié", "Mbe": "Mbé", "Meri": "Méri", "Niete": "Niété",
    "Olamze": "Olamzé", "Pette": "Petté", "Tignere": "Tignère",
    "Vele": "Vélé", "Zoetele": "Zoétélé",
}


def fix_accents(name, mapping):
    if not name:
        return name
    return mapping.get(name.strip(), name)


def get_db():
    return psycopg2.connect(**DB_CONFIG)


# ── Page routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "map_viewer.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "dgi_dashboard.html")


@app.route("/dashboard-old")
def dashboard_old():
    return send_from_directory(".", "dashboard.html")


@app.route("/<path:filename>")
def serve_static(filename):
    allowed = ('.css', '.js', '.png', '.jpg', '.svg', '.ico', '.json')
    if any(filename.endswith(ext) for ext in allowed):
        return send_from_directory(".", filename)
    return jsonify({"error": "Not found"}), 404


# ── Houses GeoJSON (existing) ────────────────────────────────────
@app.route("/api/houses")
def get_houses():
    try:
        west = float(request.args.get("west", 8.0))
        south = float(request.args.get("south", 1.0))
        east = float(request.args.get("east", 16.0))
        north = float(request.args.get("north", 13.0))
        limit = min(int(request.args.get("limit", 5000)), 10000)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameters"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT col0 AS id, col69 AS immatriculation, col31 AS building_type,
                   col67 AS area, col8 AS amenity, col12 AS name,
                   ST_AsGeoJSON(geom) AS geojson
            FROM public.houses_immat
            WHERE geom IS NOT NULL AND geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
            LIMIT %s;
        """, (west, south, east, north, limit))
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom:
                continue
            features.append({
                "type": "Feature", "geometry": geom,
                "properties": {k: row[k] for k in ["id", "immatriculation", "building_type", "area", "amenity", "name"]},
            })
        return jsonify({"type": "FeatureCollection", "features": features, "total_in_view": len(features)})
    finally:
        conn.close()


# ── Search by immatriculation ────────────────────────────────────
@app.route("/api/search")
def search_house():
    immat = request.args.get("immat", "").strip()
    if not immat:
        return jsonify({"error": "Missing immat parameter"}), 400

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT col0 AS id, col69 AS immatriculation, col31 AS building_type,
                   col67 AS area, col8 AS amenity, col12 AS name,
                   ST_AsGeoJSON(geom) AS geojson,
                   ST_X(ST_Centroid(geom)) AS center_lon, ST_Y(ST_Centroid(geom)) AS center_lat
            FROM public.houses_immat WHERE col69 = %s AND geom IS NOT NULL
        """, (immat,))
        houses = cur.fetchall()
        if not houses:
            return jsonify({"error": "Not found", "found": False}), 404

        house_features = []
        for row in houses:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if geom:
                house_features.append({"type": "Feature", "geometry": geom,
                    "properties": {k: row[k] for k in ["id", "immatriculation", "building_type", "area", "amenity", "name"]}})

        cur.execute("""
            SELECT gid, adm3_name1 AS adm3_name, adm2_name1 AS adm2_name, adm1_name, adm0_name,
                   adm3_pcode, adm2_pcode, area_sqkm, ST_AsGeoJSON(geom) AS geojson
            FROM public.cmr_admin3
            WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) LIMIT 1;
        """, (houses[0]["center_lon"], houses[0]["center_lat"]))
        admin = cur.fetchone()
        admin_feature = None
        admin_info = None
        if admin:
            admin_info = {
                "adm3_name": fix_accents(admin["adm3_name"], COMMUNE_ACCENT_FIX),
                "adm2_name": fix_accents(admin["adm2_name"], DEPT_ACCENT_FIX),
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


# ── Stats ────────────────────────────────────────────────────────
@app.route("/api/stats")
def stats():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM public.houses_immat;")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.houses_immat WHERE col69 IS NOT NULL;")
        with_immat = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT col69) FROM public.houses_immat WHERE col69 IS NOT NULL;")
        unique_immat = cur.fetchone()[0]
        return jsonify({"total_houses": total, "with_immatriculation": with_immat, "unique_immatriculations": unique_immat})
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
#  DASHBOARD API (uses pre-computed summary tables for speed)
# ══════════════════════════════════════════════════════════════════
def table_exists(cur, table):
    # Check if table exists in any schema in the search path
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = %s AND table_schema IN ('public', 'immatriculation')
        )
    """, (table,))
    res = cur.fetchone()
    if isinstance(res, dict):
        return res['exists']
    return res[0]


# ── Admin boundaries GeoJSON (using pre-computed tables) ─────────
@app.route("/api/admin/regions")
def get_admin_regions():
    """Return all 10 regions as GeoJSON with pre-computed tax stats."""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Determine if we use the summary table or fallback to the base table
        has_summary = table_exists(cur, 'tax_summary_regions')
        
        if has_summary:
            cur.execute("""
                SELECT
                    r.gid, s.name, s.name_en, ST_AsGeoJSON(r.geom) AS geojson,
                    COALESCE(s.nb_batiments, 0) AS nb_batiments,
                    COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                    COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                    COALESCE(s.nb_airbnb, 0) AS nb_airbnb,
                    COALESCE(s.nb_airbnb_matched, 0) AS nb_airbnb_matched
                FROM immatriculation.admin_regions r
                JOIN immatriculation.tax_summary_regions s ON r.gid = s.gid
                ORDER BY s.name;
            """)
        else:
            # Fallback: Just return regions without stats if the summary hasn't finished
            cur.execute("""
                SELECT
                    gid, name, name_en, ST_AsGeoJSON(geom) AS geojson,
                    0 AS nb_batiments, 0 AS surface_totale_m2, 0 AS impot_estime_fcfa,
                    0 AS nb_airbnb, 0 AS nb_airbnb_matched
                FROM immatriculation.admin_regions
                ORDER BY name;
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
                    "gid": row["gid"],
                    "name": row["name"],
                    "name_en": row["name_en"],
                    "nb_batiments": int(row["nb_batiments"]),
                    "surface_totale_m2": float(row["surface_totale_m2"]),
                    "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                    "nb_airbnb": int(row["nb_airbnb"]),
                    "nb_airbnb_matched": int(row["nb_airbnb_matched"]),
                },
            })
        return jsonify({"type": "FeatureCollection", "features": features})
    finally:
        conn.close()


@app.route("/api/admin/departments")
def get_admin_departments():
    region_filter = request.args.get("region", "").strip()
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_summary = table_exists(cur, 'tax_summary_departments')

        
        if has_summary:
            if region_filter:
                cur.execute("""
                    SELECT d.gid, s.name, s.name_en, ST_AsGeoJSON(d.geom) AS geojson,
                           COALESCE(s.nb_batiments, 0) AS nb_batiments,
                           COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                           COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                           COALESCE(s.nb_airbnb, 0) AS nb_airbnb
                    FROM immatriculation.admin_departments d
                    JOIN immatriculation.tax_summary_departments s ON d.gid = s.gid
                    WHERE ST_Contains(
                        (SELECT geom FROM immatriculation.admin_regions WHERE name = %s LIMIT 1),
                        ST_Centroid(d.geom))
                    ORDER BY s.name;
                """, [region_filter])
            else:
                cur.execute("""
                    SELECT d.gid, s.name, s.name_en, ST_AsGeoJSON(d.geom) AS geojson,
                           COALESCE(s.nb_batiments, 0) AS nb_batiments,
                           COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                           COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                           COALESCE(s.nb_airbnb, 0) AS nb_airbnb
                    FROM immatriculation.admin_departments d
                    JOIN immatriculation.tax_summary_departments s ON d.gid = s.gid ORDER BY s.name;
                """)
        else:
            if region_filter:
                cur.execute("""
                    SELECT gid, name, name_en, ST_AsGeoJSON(geom) AS geojson,
                           0 AS nb_batiments, 0 AS surface_totale_m2, 0 AS impot_estime_fcfa, 0 AS nb_airbnb
                    FROM immatriculation.admin_departments
                    WHERE ST_Contains(
                        (SELECT geom FROM immatriculation.admin_regions WHERE name = %s LIMIT 1),
                        ST_Centroid(geom))
                    ORDER BY name;
                """, [region_filter])
            else:
                cur.execute("""
                    SELECT gid, name, name_en, ST_AsGeoJSON(geom) AS geojson,
                           0 AS nb_batiments, 0 AS surface_totale_m2, 0 AS impot_estime_fcfa, 0 AS nb_airbnb
                    FROM immatriculation.admin_departments ORDER BY name;
                """)
                
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom: continue
            features.append({"type": "Feature", "geometry": geom, "properties": {
                "gid": row["gid"], "name": row["name"], "name_en": row["name_en"],
                "nb_batiments": int(row["nb_batiments"]),
                "surface_totale_m2": float(row["surface_totale_m2"]),
                "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                "nb_airbnb": int(row["nb_airbnb"]),
            }})
        return jsonify({"type": "FeatureCollection", "features": features})
    finally:
        conn.close()


@app.route("/api/admin/communes")
def get_admin_communes():
    dept_filter = request.args.get("department", "").strip()
    region_filter = request.args.get("region", "").strip()
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_summary = table_exists(cur, 'tax_summary_communes')
        
        if has_summary:
            if dept_filter:
                cur.execute("""
                    SELECT c.gid, s.name, s.dept_name, s.region_name, s.pcode, s.prix_m2_fcfa as prix_mercurial,
                           ST_AsGeoJSON(c.geom) AS geojson,
                           COALESCE(s.nb_batiments, 0) AS nb_batiments,
                           COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                           COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                           COALESCE(s.nb_airbnb, 0) AS nb_airbnb
                    FROM public.cmr_admin3 c 
                    JOIN immatriculation.tax_summary_communes s ON c.gid = s.gid
                    WHERE ST_Contains(
                        (SELECT geom FROM immatriculation.admin_departments WHERE name = %s LIMIT 1),
                        ST_Centroid(c.geom))
                    ORDER BY s.name;
                """, [dept_filter])
            elif region_filter:
                cur.execute("""
                    SELECT c.gid, s.name, s.dept_name, s.region_name, s.pcode, s.prix_m2_fcfa as prix_mercurial,
                           ST_AsGeoJSON(c.geom) AS geojson,
                           COALESCE(s.nb_batiments, 0) AS nb_batiments,
                           COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                           COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                           COALESCE(s.nb_airbnb, 0) AS nb_airbnb
                    FROM public.cmr_admin3 c 
                    JOIN immatriculation.tax_summary_communes s ON c.gid = s.gid
                    WHERE s.region_name = %s
                    ORDER BY s.name;
                """, [region_filter])
            else:
                cur.execute("""
                    SELECT c.gid, s.name, s.dept_name, s.region_name, s.pcode, s.prix_m2_fcfa as prix_mercurial,
                           ST_AsGeoJSON(c.geom) AS geojson,
                           COALESCE(s.nb_batiments, 0) AS nb_batiments,
                           COALESCE(s.surface_totale_m2, 0) AS surface_totale_m2,
                           COALESCE(s.impot_estime_fcfa, 0) AS impot_estime_fcfa,
                           COALESCE(s.nb_airbnb, 0) AS nb_airbnb
                    FROM public.cmr_admin3 c 
                    JOIN immatriculation.tax_summary_communes s ON c.gid = s.gid 
                    ORDER BY s.name;
                """)
        else:
            if dept_filter:
                cur.execute("""
                    SELECT gid, COALESCE(adm3_name, adm3_name1) as name, adm2_name1 as dept_name, 
                           adm1_name as region_name, adm3_pcode as pcode, 0 as prix_mercurial,
                           ST_AsGeoJSON(geom) AS geojson,
                           0 AS nb_batiments, 0 AS surface_totale_m2, 0 AS impot_estime_fcfa, 0 AS nb_airbnb
                    FROM cmr_admin3
                    WHERE ST_Contains(
                        (SELECT geom FROM admin_departments WHERE name = %s LIMIT 1),
                        ST_Centroid(geom))
                    ORDER BY name;
                """, [dept_filter])
            else:
                cur.execute("""
                    SELECT gid, COALESCE(adm3_name, adm3_name1) as name, adm2_name1 as dept_name, 
                           adm1_name as region_name, adm3_pcode as pcode, 0 as prix_mercurial,
                           ST_AsGeoJSON(geom) AS geojson,
                           0 AS nb_batiments, 0 AS surface_totale_m2, 0 AS impot_estime_fcfa, 0 AS nb_airbnb
                    FROM cmr_admin3 ORDER BY name;
                """)
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom: continue
            features.append({"type": "Feature", "geometry": geom, "properties": {
                "gid": row["gid"], "name": fix_accents(row["name"], COMMUNE_ACCENT_FIX),
                "dept_name": fix_accents(row["dept_name"], DEPT_ACCENT_FIX),
                "region_name": row["region_name"], "pcode": row["pcode"],
                "nb_batiments": int(row["nb_batiments"]),
                "surface_totale_m2": float(row["surface_totale_m2"]),
                "impot_estime_fcfa": float(row["impot_estime_fcfa"]),
                "prix_mercurial": int(row["prix_mercurial"]),
                "nb_airbnb": int(row["nb_airbnb"]),
            }})
        return jsonify({"type": "FeatureCollection", "features": features})
    finally:
        conn.close()


@app.route("/api/tax/summary")
def tax_summary():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT COUNT(*) AS total_batiments, COUNT(DISTINCT col69) AS total_parcelles,
                   ROUND(COALESCE(SUM(col67::numeric), 0), 0) AS surface_totale_m2,
                   COUNT(*) FILTER (WHERE col69 IS NOT NULL) AS batiments_immatricules
            FROM houses_immat WHERE geom IS NOT NULL;
        """)
        houses = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS total FROM airbnb_listings;")
        airbnb_total = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM airbnb_listings WHERE matched_immat IS NOT NULL;")
        airbnb_matched = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM mercuriale_prix;")
        mercuriale_count = cur.fetchone()["total"]
        return jsonify({
            "total_batiments": houses["total_batiments"],
            "total_parcelles": houses["total_parcelles"],
            "batiments_immatricules": houses["batiments_immatricules"],
            "surface_totale_m2": float(houses["surface_totale_m2"]),
            "airbnb_total": airbnb_total, "airbnb_matched": airbnb_matched,
            "mercuriale_arrondissements": mercuriale_count,
        })
    finally:
        conn.close()


@app.route("/api/airbnb")
def get_airbnb():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, ext_id, title, lat, lon, url,
                   matched_building_id, matched_immat,
                   ROUND(match_distance_m::numeric, 1) AS match_distance_m,
                   matched_commune, matched_departement, matched_region,
                   ST_AsGeoJSON(geom) AS geojson
            FROM immatriculation.airbnb_listings ORDER BY id;
        """)
        rows = cur.fetchall()
        features = []
        for row in rows:
            geom = json.loads(row["geojson"]) if row["geojson"] else None
            if not geom: continue
            features.append({"type": "Feature", "geometry": geom, "properties": {
                "id": row["id"], "title": row["title"], "url": row["url"],
                "matched_immat": row["matched_immat"],
                "match_distance_m": float(row["match_distance_m"]) if row["match_distance_m"] else None,
                "matched_commune": row["matched_commune"], "matched_region": row["matched_region"],
                "is_matched": row["matched_immat"] is not None,
            }})
        return jsonify({"type": "FeatureCollection", "features": features})
    finally:
        conn.close()


# ── Building polygons API (for commune-level view) ───────────────
@app.route("/api/buildings")
def get_buildings():
    """Return building polygons with tax info for a given commune or viewport."""
    commune_gid = request.args.get("commune_gid", type=int)
    west = request.args.get("west", type=float)
    south = request.args.get("south", type=float)
    east = request.args.get("east", type=float)
    north = request.args.get("north", type=float)
    limit = min(int(request.args.get("limit", 5000)), 10000)
    
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if commune_gid:
            # Get buildings in a specific commune
            cur.execute("""
                SELECT h.col0 AS osm_id, h.col69 AS immatriculation, 
                       h.col31 AS building_type, h.col8 AS amenity, h.col12 AS name,
                       ROUND(h.col67::numeric, 2) AS area_m2,
                       ROUND((h.col67::numeric * cp.prix_m2_fcfa * cp.redevance_rate)::numeric, 0) AS impot_annuel,
                       cp.prix_m2_fcfa,
                       ST_AsGeoJSON(h.geom) AS geojson
                FROM public.houses_immat h
                LEFT JOIN immatriculation.commune_prices cp ON h.commune_gid = cp.commune_gid
                WHERE h.commune_gid = %s AND h.geom IS NOT NULL
                LIMIT %s;
            """, (commune_gid, limit))
        elif all([west, south, east, north]):
            # Get buildings in viewport
            cur.execute("""
                SELECT h.col0 AS osm_id, h.col69 AS immatriculation, 
                       h.col31 AS building_type, h.col8 AS amenity, h.col12 AS name,
                       ROUND(h.col67::numeric, 2) AS area_m2,
                       ROUND((h.col67::numeric * COALESCE(cp.prix_m2_fcfa, 500) * COALESCE(cp.redevance_rate, 0.25))::numeric, 0) AS impot_annuel,
                       COALESCE(cp.prix_m2_fcfa, 500) AS prix_m2_fcfa,
                       ST_AsGeoJSON(h.geom) AS geojson
                FROM public.houses_immat h
                LEFT JOIN immatriculation.commune_prices cp ON h.commune_gid = cp.commune_gid
                WHERE h.geom IS NOT NULL 
                  AND h.geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                LIMIT %s;
            """, (west, south, east, north, limit))
        else:
            return jsonify({"error": "Provide commune_gid or viewport bounds (west,south,east,north)"}), 400
        
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
                    "osm_id": row["osm_id"],
                    "immatriculation": row["immatriculation"],
                    "building_type": row["building_type"] or "residential",
                    "amenity": row["amenity"],
                    "name": row["name"],
                    "area_m2": float(row["area_m2"]) if row["area_m2"] else 0,
                    "impot_annuel": int(row["impot_annuel"]) if row["impot_annuel"] else 0,
                    "prix_m2_fcfa": int(row["prix_m2_fcfa"]) if row["prix_m2_fcfa"] else 500,
                }
            })
        return jsonify({
            "type": "FeatureCollection", 
            "features": features,
            "count": len(features),
            "limit": limit
        })
    finally:
        conn.close()


@app.route("/houses-map")
def houses_map():
    return send_from_directory(".", "houses_map.html")


# ── Registered Houses (immatriculation app DB) ───────────────────
@app.route("/api/registered-houses")
def get_registered_houses():
    """Return registered houses from the houses table as GeoJSON points."""
    payment_status = request.args.get("payment_status", "").strip().upper()
    verification_status = request.args.get("verification_status", "").strip().upper()
    commune_filter = request.args.get("commune", "").strip()
    search = request.args.get("search", "").strip()
    limit = min(int(request.args.get("limit", 2000)), 5000)

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        conditions = ["gps_latitude IS NOT NULL", "gps_longitude IS NOT NULL"]
        params = []

        if payment_status:
            conditions.append("payment_status = %s")
            params.append(payment_status)
        if verification_status:
            conditions.append("verification_status = %s")
            params.append(verification_status)
        if commune_filter:
            conditions.append("commune ILIKE %s")
            params.append(f"%{commune_filter}%")
        if search:
            conditions.append("immatriculation_number ILIKE %s")
            params.append(f"%{search}%")

        where = "WHERE " + " AND ".join(conditions)
        params.append(limit)

        cur.execute(f"""
            SELECT house_id, immatriculation_number, commune, department, region, quartier,
                   building_type, building_levels,
                   ROUND(footprint_area::numeric, 1) AS footprint_area,
                   construction_year, wall_material, roof_material,
                   owner_name, phone_number, verification_status, payment_status,
                   ROUND(annual_tax_amount::numeric, 0) AS annual_tax_amount,
                   ROUND(gps_latitude::numeric, 7) AS lat,
                   ROUND(gps_longitude::numeric, 7) AS lon,
                   ROUND(confidence_score::numeric, 2) AS confidence_score,
                   TO_CHAR(detected_date, 'YYYY-MM-DD') AS detected_date
            FROM houses
            {where}
            ORDER BY house_id
            LIMIT %s
        """, params)
        rows = cur.fetchall()

        features = []
        for row in rows:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["lon"]), float(row["lat"])]
                },
                "properties": {
                    "id": row["house_id"],
                    "immat": row["immatriculation_number"],
                    "commune": row["commune"] or "–",
                    "department": row["department"] or "–",
                    "region": row["region"] or "–",
                    "quartier": row["quartier"] or "–",
                    "building_type": row["building_type"] or "–",
                    "building_levels": row["building_levels"] or 1,
                    "footprint_area": float(row["footprint_area"]) if row["footprint_area"] else None,
                    "construction_year": row["construction_year"],
                    "wall_material": row["wall_material"] or "–",
                    "roof_material": row["roof_material"] or "–",
                    "owner_name": row["owner_name"] or "–",
                    "phone_number": row["phone_number"] or "–",
                    "verification_status": row["verification_status"],
                    "payment_status": row["payment_status"],
                    "annual_tax": float(row["annual_tax_amount"]) if row["annual_tax_amount"] else None,
                    "confidence": float(row["confidence_score"]) if row["confidence_score"] else 0,
                    "detected_date": row["detected_date"] or "–",
                }
            })
        return jsonify({
            "type": "FeatureCollection",
            "features": features,
            "count": len(features)
        })
    finally:
        conn.close()


@app.route("/api/registered-stats")
def get_registered_stats():
    """Summary statistics for the registered houses table."""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
                COUNT(*)                                                     AS total,
                COUNT(*) FILTER (WHERE gps_latitude IS NOT NULL)            AS with_coords,
                COUNT(*) FILTER (WHERE payment_status = 'PAID')             AS paid,
                COUNT(*) FILTER (WHERE payment_status = 'PARTIAL')          AS partial,
                COUNT(*) FILTER (WHERE payment_status = 'UNPAID')           AS unpaid,
                COUNT(*) FILTER (WHERE verification_status = 'VERIFIED')    AS verified,
                COUNT(*) FILTER (WHERE verification_status = 'PENDING')     AS pending,
                COALESCE(SUM(annual_tax_amount), 0)                         AS total_tax_expected,
                COALESCE(SUM(annual_tax_amount) FILTER (WHERE payment_status = 'PAID'), 0) AS total_tax_collected
            FROM houses
        """)
        row = cur.fetchone()
        return jsonify({
            "total":               int(row["total"]),
            "with_coords":         int(row["with_coords"]),
            "paid":                int(row["paid"]),
            "partial":             int(row["partial"]),
            "unpaid":              int(row["unpaid"]),
            "verified":            int(row["verified"]),
            "pending":             int(row["pending"]),
            "total_tax_expected":  float(row["total_tax_expected"]),
            "total_tax_collected": float(row["total_tax_collected"]),
        })
    finally:
        conn.close()


if __name__ == "__main__":
    print("Map server starting at http://localhost:5556")
    print("  DGI Dashboard:   http://localhost:5556/dashboard")
    print("  Houses Map:      http://localhost:5556/houses-map")
    print("  API:  /api/admin/regions, /api/admin/departments, /api/admin/communes")
    print("        /api/tax/summary, /api/airbnb, /api/buildings, /api/houses, /api/search")
    try:
        from waitress import serve
        print("  (serving with waitress)")
        serve(app, host="127.0.0.1", port=5556, threads=4)
    except ImportError:
        app.run(host="127.0.0.1", port=5556, debug=False, use_reloader=False, threaded=True)
