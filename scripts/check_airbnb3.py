import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

# 1) Building types for Airbnb-matched buildings
print("=== Building types of Airbnb-matched buildings ===")
cur.execute("""
    SELECT h.col31 AS building_type, COUNT(*) AS cnt
    FROM immatriculation.airbnb_listings ab
    JOIN houses_immat h ON ab.matched_building_id = h.col0
    GROUP BY h.col31 ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':20s} {r[1]}")

# 2) Why no tax? Check commune names vs mercuriale
print("\n=== Airbnb commune distribution ===")
cur.execute("""
    SELECT ab.matched_commune, COUNT(*) AS cnt,
           m.commune_name IS NOT NULL AS has_mercuriale
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN immatriculation.mercuriale_lookup m
           ON lower(ab.matched_commune) = lower(m.commune_name)
    GROUP BY ab.matched_commune, m.commune_name IS NOT NULL
    ORDER BY cnt DESC LIMIT 20
""")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':25s} count={r[1]:>4}  mercuriale={'YES' if r[2] else 'NO'}")

# 3) Check what mercuriale commune names look like for Yaoundé
print("\n=== Mercuriale commune names containing 'yaound' ===")
cur.execute("SELECT commune_name, prix_m2_fcfa FROM immatriculation.mercuriale_lookup WHERE lower(commune_name) LIKE '%yaound%'")
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]} FCFA/m2")

# 4) Check what mercuriale commune names look like for Douala
print("\n=== Mercuriale commune names containing 'douala' ===")
cur.execute("SELECT commune_name, prix_m2_fcfa FROM immatriculation.mercuriale_lookup WHERE lower(commune_name) LIKE '%douala%'")
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]} FCFA/m2")

# 5) What admin commune names do Airbnb use?
print("\n=== Unique Airbnb communes (top 15) ===")
cur.execute("SELECT matched_commune, COUNT(*) FROM immatriculation.airbnb_listings GROUP BY matched_commune ORDER BY 2 DESC LIMIT 15")
for r in cur.fetchall():
    print(f"  {r[0] or 'NULL':25s} {r[1]}")

conn.close()
