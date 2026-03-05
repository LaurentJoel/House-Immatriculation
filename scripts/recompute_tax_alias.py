"""Recompute tax_summary_regions and tax_summary_communes using commune_name_alias."""
import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor()

# Recompute tax_summary_communes
cur.execute("DROP TABLE IF EXISTS immatriculation.tax_summary_communes;")
cur.execute("""
    CREATE TABLE immatriculation.tax_summary_communes AS
    SELECT a.adm3_name1 AS commune,
           a.adm2_name1 AS departement,
           a.adm1_name  AS region,
           COUNT(*) AS total_buildings,
           COUNT(CASE WHEN h.col69 IS NOT NULL THEN 1 END) AS immatriculated,
           m.prix_m2_fcfa,
           ROUND(SUM(
               CASE WHEN h.col67 IS NOT NULL AND m.prix_m2_fcfa IS NOT NULL
                    THEN CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25
                    ELSE 0 END
           ))::bigint AS estimated_tax_total
    FROM public.houses_immat h
    JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
    GROUP BY a.adm3_name1, a.adm2_name1, a.adm1_name, m.prix_m2_fcfa
    ORDER BY estimated_tax_total DESC;
""")
print("tax_summary_communes recomputed")

# Recompute tax_summary_regions
cur.execute("DROP TABLE IF EXISTS immatriculation.tax_summary_regions;")
cur.execute("""
    CREATE TABLE immatriculation.tax_summary_regions AS
    SELECT a.adm1_name AS region,
           COUNT(*) AS total_buildings,
           COUNT(CASE WHEN h.col69 IS NOT NULL THEN 1 END) AS immatriculated,
           ROUND(SUM(
               CASE WHEN h.col67 IS NOT NULL AND m.prix_m2_fcfa IS NOT NULL
                    THEN CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25
                    ELSE 0 END
           ))::bigint AS estimated_tax_total
    FROM public.houses_immat h
    JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE (h.col67 IS NULL OR CAST(h.col67 AS float) < 500000)
    GROUP BY a.adm1_name
    ORDER BY estimated_tax_total DESC;
""")
print("tax_summary_regions recomputed")

conn.commit()

# Show results
cur.execute("SELECT region, total_buildings, immatriculated, estimated_tax_total FROM immatriculation.tax_summary_regions ORDER BY estimated_tax_total DESC;")
print("\n=== REGIONS ===")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]:,} buildings, {r[2]:,} immat, {r[3]:,} FCFA tax")

cur.execute("SELECT commune, region, total_buildings, prix_m2_fcfa, estimated_tax_total FROM immatriculation.tax_summary_communes ORDER BY estimated_tax_total DESC LIMIT 15;")
print("\n=== TOP 15 COMMUNES ===")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]}): {r[2]:,} buildings, {r[3]} FCFA/m², {r[4]:,} FCFA tax")

cur.close()
conn.close()
print("\nDone!")
