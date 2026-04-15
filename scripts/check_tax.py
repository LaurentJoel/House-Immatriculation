import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()
cur.execute("""
    SELECT a.adm1_name AS region,
           COUNT(*) AS nb,
           SUM(CAST(h.col67 AS float)) AS total_surface,
           SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa,0) * 0.25) AS total_impot
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.mercuriale_lookup m ON lower(a.adm3_name1) = lower(m.commune_name)
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY a.adm1_name
    ORDER BY total_impot DESC
""")
print(f"{'Region':20s} {'Count':>10s} {'Surface m2':>18s} {'Impot FCFA':>20s}")
print("-" * 75)
for r in cur.fetchall():
    region = r[0] or 'NULL'
    print(f"{region:20s} {r[1]:>10,} {float(r[2]):>18,.0f} {float(r[3]):>20,.0f}")
conn.close()
