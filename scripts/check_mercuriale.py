"""
Check all mercuriale commune names to build a proper mapping strategy.
"""
import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

print("=== All mercuriale commune names ===")
cur.execute("SELECT commune_name, prix_m2_fcfa FROM immatriculation.mercuriale_lookup ORDER BY commune_name")
merc = cur.fetchall()
for r in merc:
    print(f"  {r[0]:40s} {r[1]:>8} FCFA/m2")
print(f"\nTotal mercuriale entries: {len(merc)}")

print("\n=== All admin commune names (cmr_admin3) that DON'T match mercuriale ===")
cur.execute("""
    SELECT DISTINCT a.adm3_name1
    FROM cmr_admin3 a
    WHERE NOT EXISTS (
        SELECT 1 FROM immatriculation.mercuriale_lookup m
        WHERE lower(a.adm3_name1) = lower(m.commune_name)
    )
    ORDER BY a.adm3_name1
""")
unmatched = cur.fetchall()
print(f"Unmatched admin communes: {len(unmatched)}")
for r in unmatched[:30]:
    print(f"  {r[0]}")
if len(unmatched) > 30:
    print(f"  ... and {len(unmatched)-30} more")

print("\n=== Admin communes containing 'yaound' or 'douala' ===")
cur.execute("SELECT DISTINCT adm3_name1 FROM cmr_admin3 WHERE lower(adm3_name1) LIKE '%yaound%' OR lower(adm3_name1) LIKE '%douala%' ORDER BY 1")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
