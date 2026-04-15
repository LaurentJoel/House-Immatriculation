"""Check area and tax computation for Airbnb."""
import psycopg2, psycopg2.extras

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT COUNT(*) AS total,
           COUNT(h.col67) AS with_area,
           COUNT(CASE WHEN h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 0 THEN 1 END) AS area_gt0,
           COUNT(h.commune_gid) AS with_commune_gid,
           COUNT(m.prix_m2_fcfa) AS with_prix,
           COUNT(CASE WHEN h.col67 IS NOT NULL AND m.prix_m2_fcfa IS NOT NULL THEN 1 END) AS computable_tax
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
""")
r = cur.fetchone()
for k, v in r.items():
    print(f"  {k}: {v}")

# Check why 149 don't have commune_gid — maybe they need spatial assignment
cur.execute("""
    SELECT COUNT(*) AS no_commune_gid
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE h.commune_gid IS NULL
""")
print(f"\nBuildings matched but no commune_gid: {cur.fetchone()['no_commune_gid']}")

# Can we assign commune via spatial join for those?
cur.execute("""
    SELECT h.col0, a.gid, a.adm3_name1
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    LEFT JOIN cmr_admin3 a ON ST_Intersects(ST_Centroid(h.geom), a.geom) AND ST_Area(a.geom::geography) < 500000000
    WHERE h.commune_gid IS NULL
    LIMIT 5
""")
print("\nSample spatial admin assignment for buildings without commune_gid:")
for r in cur.fetchall():
    print(f"  col0={r['col0']}  -> admin gid={r['gid']}  commune={r['adm3_name1']}")

cur.close()
conn.close()
