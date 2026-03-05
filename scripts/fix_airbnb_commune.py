"""Fix 149 Airbnb matched buildings that have NULL commune_gid by spatial assignment."""
import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor()

# Update commune_gid via spatial join for buildings matched to Airbnb that lack it
cur.execute("""
    UPDATE houses_immat h
    SET commune_gid = sub.admin_gid
    FROM (
        SELECT DISTINCT ab.matched_building_id AS bid, a.gid AS admin_gid
        FROM immatriculation.airbnb_listings ab
        JOIN houses_immat h2 ON ab.matched_building_id = h2.col0
        JOIN cmr_admin3 a ON ST_Intersects(ST_Centroid(h2.geom), a.geom) 
                          AND ST_Area(a.geom::geography) < 500000000
        WHERE h2.commune_gid IS NULL
    ) sub
    WHERE h.col0 = sub.bid;
""")
print(f"Updated {cur.rowcount} buildings with commune_gid via spatial join")
conn.commit()

# Verify
cur.execute("""
    SELECT COUNT(*) FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE h.commune_gid IS NULL
""")
print(f"Remaining without commune_gid: {cur.fetchone()[0]}")

# Now count full chain again
cur.execute("""
    SELECT COUNT(*) AS total,
           COUNT(m.prix_m2_fcfa) AS with_prix,
           COUNT(CASE WHEN h.col67 IS NOT NULL AND m.prix_m2_fcfa IS NOT NULL THEN 1 END) AS computable_tax
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
""")
r = cur.fetchone()
print(f"Total={r[0]}  with_prix={r[1]}  computable_tax={r[2]}")

cur.close()
conn.close()
