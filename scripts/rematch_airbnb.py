"""
Re-match all 752 Airbnb listings to the nearest REAL building (area < 500,000 m2)
within 200m, updating matched_building_id, matched_immat, match_distance_m,
and admin info (commune, departement, region).
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

print("Re-matching Airbnb listings to real buildings (area < 500,000 m2) ...")

# Use LATERAL join to find the nearest real building for each Airbnb listing
cur.execute("""
    UPDATE immatriculation.airbnb_listings ab
    SET matched_building_id = sub.new_building_id,
        matched_immat       = sub.new_immat,
        match_distance_m    = sub.new_dist,
        matched_commune     = sub.commune,
        matched_departement = sub.departement,
        matched_region      = sub.region
    FROM (
        SELECT ab2.id AS airbnb_id,
               nearest.col0 AS new_building_id,
               nearest.col69 AS new_immat,
               nearest.dist AS new_dist,
               nearest.commune,
               nearest.departement,
               nearest.region
        FROM immatriculation.airbnb_listings ab2
        CROSS JOIN LATERAL (
            SELECT h.col0, h.col69,
                   ST_Distance(ab2.geom::geography, h.geom::geography) AS dist,
                   a.adm3_name1 AS commune,
                   a.adm2_name1 AS departement,
                   a.adm1_name AS region
            FROM houses_immat h
            LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
            WHERE h.geom IS NOT NULL
              AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
              AND ST_DWithin(ab2.geom::geography, h.geom::geography, 200)
            ORDER BY ab2.geom <-> h.geom
            LIMIT 1
        ) nearest
    ) sub
    WHERE ab.id = sub.airbnb_id
""")
matched = cur.rowcount
print(f"  Updated {matched} listings with real building match")

# Check how many couldn't find a real building within 200m
cur.execute("""
    SELECT COUNT(*) FROM immatriculation.airbnb_listings ab
    WHERE NOT EXISTS (
        SELECT 1 FROM houses_immat h
        WHERE h.geom IS NOT NULL
          AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
          AND ST_DWithin(ab.geom::geography, h.geom::geography, 200)
    )
""")
unmatched = cur.fetchone()[0]
print(f"  {unmatched} listings have no real building within 200m")

# For those, try 500m
if unmatched > 0:
    cur.execute("""
        UPDATE immatriculation.airbnb_listings ab
        SET matched_building_id = sub.new_building_id,
            matched_immat       = sub.new_immat,
            match_distance_m    = sub.new_dist,
            matched_commune     = sub.commune,
            matched_departement = sub.departement,
            matched_region      = sub.region
        FROM (
            SELECT ab2.id AS airbnb_id,
                   nearest.col0 AS new_building_id,
                   nearest.col69 AS new_immat,
                   nearest.dist AS new_dist,
                   nearest.commune, nearest.departement, nearest.region
            FROM immatriculation.airbnb_listings ab2
            CROSS JOIN LATERAL (
                SELECT h.col0, h.col69,
                       ST_Distance(ab2.geom::geography, h.geom::geography) AS dist,
                       a.adm3_name1 AS commune, a.adm2_name1 AS departement, a.adm1_name AS region
                FROM houses_immat h
                LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
                WHERE h.geom IS NOT NULL
                  AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
                  AND ST_DWithin(ab2.geom::geography, h.geom::geography, 500)
                ORDER BY ab2.geom <-> h.geom
                LIMIT 1
            ) nearest
            WHERE NOT EXISTS (
                SELECT 1 FROM houses_immat h2
                WHERE h2.geom IS NOT NULL
                  AND (h2.col67 IS NULL OR CAST(h2.col67 AS float) < 500000)
                  AND ST_DWithin(ab2.geom::geography, h2.geom::geography, 200)
            )
        ) sub
        WHERE ab.id = sub.airbnb_id
    """)
    print(f"  Extended search (500m): updated {cur.rowcount} more")

conn.commit()

# Summary
cur.execute("""
    SELECT COUNT(*) AS total,
           COUNT(matched_building_id) FILTER (WHERE matched_building_id IS NOT NULL) AS with_match,
           COUNT(matched_immat) FILTER (WHERE matched_immat IS NOT NULL AND matched_immat != '') AS with_immat,
           AVG(match_distance_m) AS avg_dist,
           MAX(match_distance_m) AS max_dist
    FROM immatriculation.airbnb_listings
""")
r = cur.fetchone()
print(f"\nFinal stats: {r[0]} total, {r[1]} matched, {r[2]} with immatriculation")
print(f"  Avg distance: {r[3]:.1f}m, Max distance: {r[4]:.1f}m")

# Verify no more giant matches
cur.execute("""
    SELECT COUNT(*)
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE CAST(h.col67 AS float) >= 500000
""")
print(f"  Still matched to giant polygons: {cur.fetchone()[0]}")

conn.close()
print("Done!")
