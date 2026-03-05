"""
Recompute tax_summary_regions and tax_summary_communes with area < 500000 filter
to exclude the giant OSM boundary polygons that were inflating the estimates.
"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

print("Recomputing tax_summary_regions ...")
cur.execute("DELETE FROM immatriculation.tax_summary_regions;")
cur.execute("""
    INSERT INTO immatriculation.tax_summary_regions
        (name, name_en, nb_batiments, surface_totale_m2, impot_estime_fcfa, prix_mercurial_moyen, nb_airbnb)
    SELECT
        a.adm1_name AS name,
        a.adm1_name AS name_en,
        COUNT(*)::int AS nb_batiments,
        COALESCE(SUM(CAST(h.col67 AS float)), 0) AS surface_totale_m2,
        COALESCE(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25), 0) AS impot_estime_fcfa,
        COALESCE(AVG(m.prix_m2_fcfa), 0) AS prix_mercurial_moyen,
        0 AS nb_airbnb
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.mercuriale_lookup m ON lower(a.adm3_name1) = lower(m.commune_name)
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY a.adm1_name
    ORDER BY impot_estime_fcfa DESC
""")
print(f"  Inserted {cur.rowcount} rows into tax_summary_regions")

# Update airbnb counts per region
cur.execute("""
    UPDATE immatriculation.tax_summary_regions r
    SET nb_airbnb = sub.cnt
    FROM (
        SELECT a.adm1_name, COUNT(*) AS cnt
        FROM immatriculation.airbnb_listings ab
        JOIN cmr_admin3 a ON ST_Within(ab.geom, a.geom)
        GROUP BY a.adm1_name
    ) sub
    WHERE r.name = sub.adm1_name
""")
print(f"  Updated airbnb counts in {cur.rowcount} rows")

print("Recomputing tax_summary_communes ...")
cur.execute("DELETE FROM immatriculation.tax_summary_communes;")
cur.execute("""
    INSERT INTO immatriculation.tax_summary_communes
        (name, dept_name, region_name, prix_m2_fcfa, nb_batiments, surface_totale_m2, impot_estime_fcfa, nb_airbnb, nb_airbnb_matched)
    SELECT
        a.adm3_name1 AS name,
        a.adm2_name1 AS dept_name,
        a.adm1_name AS region_name,
        COALESCE(m.prix_m2_fcfa, 0) AS prix_m2_fcfa,
        COUNT(*)::int AS nb_batiments,
        COALESCE(SUM(CAST(h.col67 AS float)), 0) AS surface_totale_m2,
        COALESCE(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25), 0) AS impot_estime_fcfa,
        0 AS nb_airbnb,
        0 AS nb_airbnb_matched
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.mercuriale_lookup m ON lower(a.adm3_name1) = lower(m.commune_name)
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY a.adm3_name1, a.adm2_name1, a.adm1_name, m.prix_m2_fcfa
    ORDER BY impot_estime_fcfa DESC
""")
print(f"  Inserted {cur.rowcount} rows into tax_summary_communes")

conn.commit()
conn.close()
print("Done! Tax summaries recomputed with area < 500,000 m2 filter.")
