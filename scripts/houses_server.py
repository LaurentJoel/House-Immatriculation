"""
Lightweight server for the Houses Map page.
Run: python houses_server.py
"""
import json, os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

@app.route("/")
def index():
    return send_from_directory(SCRIPT_DIR, "houses_map.html")

@app.route("/dashboard")
def dashboard():
    return send_from_directory(SCRIPT_DIR, "dgi_dashboard.html")

@app.route("/api/stats")
def stats():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM public.houses_immat;")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM public.houses_immat WHERE col69 IS NOT NULL;")
        with_immat = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT col69) FROM public.houses_immat WHERE col69 IS NOT NULL;")
        unique = cur.fetchone()[0]
        return jsonify({"total_houses": total, "with_immatriculation": with_immat, "unique_immatriculations": unique})
    finally:
        conn.close()

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
    conn = psycopg2.connect(**DB_CONFIG)
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

@app.route("/api/search")
def search_house():
    immat = request.args.get("immat", "").strip()
    if not immat:
        return jsonify({"error": "Missing immat parameter"}), 400
    conn = psycopg2.connect(**DB_CONFIG)
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

if __name__ == "__main__":
    print("Houses Map Server on http://localhost:5555", flush=True)
    from waitress import serve
    serve(app, host="127.0.0.1", port=5555, threads=4)
