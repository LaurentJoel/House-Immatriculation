"""Diagnose why Airbnb buildings have no tax in the API."""
import psycopg2, psycopg2.extras

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Check a few Airbnb matched buildings for commune_gid and admin join
cur.execute("""
    SELECT ab.id, ab.title, ab.matched_building_id, ab.matched_commune,
           h.commune_gid, h.col31 AS building_type,
           a.adm3_name1, ca.mercuriale_name, m.prix_m2_fcfa
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    LIMIT 10;
""")
for r in cur.fetchall():
    print(f"id={r['id']} title={r['title'][:30]:30s}  bid={r['matched_building_id']}  commune_gid={r['commune_gid']}  admin3={r['adm3_name1']}  alias={r['mercuriale_name']}  prix={r['prix_m2_fcfa']}  type={r['building_type']}")

# Count how many matched buildings have commune_gid
cur.execute("""
    SELECT COUNT(*) AS total,
           COUNT(h.commune_gid) AS with_commune_gid,
           COUNT(a.adm3_name1) AS with_admin,
           COUNT(ca.mercuriale_name) AS with_alias,
           COUNT(m.prix_m2_fcfa) AS with_prix
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
""")
r = cur.fetchone()
print(f"\nTotal={r['total']}  with_commune_gid={r['with_commune_gid']}  with_admin={r['with_admin']}  with_alias={r['with_alias']}  with_prix={r['with_prix']}")

cur.close()
conn.close()
