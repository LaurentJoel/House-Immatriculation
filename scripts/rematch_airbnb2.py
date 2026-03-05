"""
Re-match Airbnb listings to nearest real building, row by row for reliability.
Uses KNN via <-> operator with a geometry-based distance filter.
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
conn.autocommit = False
cur = conn.cursor()

# Get all airbnb listings
cur.execute("SELECT id, ST_X(geom) AS lon, ST_Y(geom) AS lat FROM immatriculation.airbnb_listings ORDER BY id")
listings = cur.fetchall()
print(f"Processing {len(listings)} Airbnb listings...")

matched = 0
not_found = 0

for i, (ab_id, lon, lat) in enumerate(listings):
    # Find nearest real building using KNN <-> operator with bbox pre-filter
    cur.execute("""
        SELECT h.col0, h.col69, h.col67,
               ST_Distance(h.geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS dist_m,
               a.adm3_name1, a.adm2_name1, a.adm1_name
        FROM houses_immat h
        LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
        WHERE h.geom IS NOT NULL
          AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
          AND h.geom && ST_Expand(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 0.005)
        ORDER BY h.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT 1
    """, (lon, lat, lon, lat, lon, lat))
    
    row = cur.fetchone()
    if row:
        building_id, immat, area, dist_m, commune, dept, region = row
        cur.execute("""
            UPDATE immatriculation.airbnb_listings
            SET matched_building_id = %s, matched_immat = %s,
                match_distance_m = %s,
                matched_commune = %s, matched_departement = %s, matched_region = %s
            WHERE id = %s
        """, (str(building_id), immat, dist_m, commune, dept, region, ab_id))
        matched += 1
    else:
        not_found += 1
    
    if (i + 1) % 50 == 0:
        conn.commit()
        print(f"  {i+1}/{len(listings)} processed ({matched} matched, {not_found} not found)")

conn.commit()
print(f"\nDone! {matched} matched, {not_found} not found out of {len(listings)}")

# Verify
cur.execute("""
    SELECT COUNT(*) AS total,
           COUNT(*) FILTER (WHERE matched_immat IS NOT NULL AND matched_immat != '') AS with_immat,
           AVG(match_distance_m)::numeric(10,1) AS avg_dist,
           MAX(match_distance_m)::numeric(10,1) AS max_dist
    FROM immatriculation.airbnb_listings
    WHERE matched_building_id IS NOT NULL
""")
r = cur.fetchone()
print(f"Stats: {r[0]} matched total, {r[1]} with immatriculation, avg dist={r[2]}m, max dist={r[3]}m")

# Verify no giant matches
cur.execute("""
    SELECT COUNT(*)
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE CAST(h.col67 AS float) >= 500000
""")
print(f"Still matched to giant polygons: {cur.fetchone()[0]}")

conn.close()
