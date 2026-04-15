import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

# How many airbnb are matched to giant polygons vs real buildings?
print("=== Airbnb match quality ===")
cur.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE CAST(h.col67 AS float) < 500000) AS matched_real,
        COUNT(*) FILTER (WHERE CAST(h.col67 AS float) >= 500000) AS matched_giant,
        COUNT(*) FILTER (WHERE h.col0 IS NULL) AS no_match
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
""")
r = cur.fetchone()
print(f"Total: {r[0]}, matched to real building: {r[1]}, matched to giant polygon: {r[2]}, no match: {r[3]}")

# Check unique giant polygon ids
cur.execute("""
    SELECT h.col0, CAST(h.col67 AS float) AS area, COUNT(*) AS airbnb_count
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE CAST(h.col67 AS float) >= 500000
    GROUP BY h.col0, h.col67
    ORDER BY airbnb_count DESC
    LIMIT 10
""")
print("\nGiant polygon matches:")
for r in cur.fetchall():
    print(f"  building {r[0]}: area={r[1]:,.0f} m2, airbnb_count={r[2]}")

# Check: can we find the REAL nearest building for each airbnb?
print("\n=== Test re-matching (5 airbnb) ===")
cur.execute("""
    SELECT ab.id, ab.title, ab.lat, ab.lon,
           nearest.col0 AS new_building_id, nearest.col67 AS area, nearest.col69 AS immat, nearest.dist
    FROM immatriculation.airbnb_listings ab
    CROSS JOIN LATERAL (
        SELECT h.col0, h.col67, h.col69,
               ST_Distance(ab.geom::geography, h.geom::geography) AS dist
        FROM houses_immat h
        WHERE h.geom IS NOT NULL
          AND (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
          AND ST_DWithin(ab.geom::geography, h.geom::geography, 200)
        ORDER BY ab.geom <-> h.geom
        LIMIT 1
    ) nearest
    LIMIT 5
""")
cols = [d[0] for d in cur.description]
for row in cur.fetchall():
    d = dict(zip(cols, row))
    print(f"  Airbnb #{d['id']} '{d['title'][:40]}' -> building {d['new_building_id']}, area={d['area']}, immat={d['immat']}, dist={d['dist']:.1f}m")

conn.close()
