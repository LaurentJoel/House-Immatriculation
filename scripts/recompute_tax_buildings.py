"""Recompute tax summaries with building-only filters (no farmland/forest/meadow, area < 10000 m²)."""
import psycopg2

NON_BUILDING_TYPES = (
    'farmland', 'forest', 'meadow', 'orchard', 'quarry', 'plant_nursery',
    'military', 'railway', 'cemetery', 'village_green', 'greenfield',
    'brownfield', 'grass', 'farmyard', 'allotments', 'basin',
    'recreation_ground', 'landfill', 'reservoir',
)
MAX_AREA = 10000

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor()

BUILDING_FILTER = """
    h.col67 IS NOT NULL
    AND CAST(h.col67 AS float) < %s
    AND (h.col31 IS NULL OR h.col31 NOT IN %s)
"""

# ── tax_summary_regions ──
cur.execute("DROP TABLE IF EXISTS immatriculation.tax_summary_regions;")
cur.execute("""
    CREATE TABLE immatriculation.tax_summary_regions AS
    SELECT a.adm1_name AS name,
           a.adm1_name AS name_en,
           COUNT(*) AS nb_batiments,
           ROUND(SUM(CAST(h.col67 AS float)))::bigint AS surface_totale_m2,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS impot_estime_fcfa,
           ROUND(AVG(m.prix_m2_fcfa))::int AS prix_mercurial_moyen,
           (SELECT COUNT(*) FROM immatriculation.airbnb_listings ab2
            WHERE ab2.matched_region = a.adm1_name) AS nb_airbnb
    FROM public.houses_immat h
    JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL
      AND CAST(h.col67 AS float) < %s
      AND (h.col31 IS NULL OR h.col31 NOT IN %s)
    GROUP BY a.adm1_name
    ORDER BY impot_estime_fcfa DESC;
""", (MAX_AREA, NON_BUILDING_TYPES))
print("tax_summary_regions recomputed")

# ── tax_summary_communes ──
cur.execute("DROP TABLE IF EXISTS immatriculation.tax_summary_communes;")
cur.execute("""
    CREATE TABLE immatriculation.tax_summary_communes AS
    SELECT a.adm3_name1 AS name,
           a.adm2_name1 AS dept_name,
           a.adm1_name AS region_name,
           m.prix_m2_fcfa,
           COUNT(*) AS nb_batiments,
           ROUND(SUM(CAST(h.col67 AS float)))::bigint AS surface_totale_m2,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS impot_estime_fcfa,
           (SELECT COUNT(*) FROM immatriculation.airbnb_listings ab2
            WHERE ab2.matched_commune = a.adm3_name1) AS nb_airbnb,
           (SELECT COUNT(*) FROM immatriculation.airbnb_listings ab3
            WHERE ab3.matched_commune = a.adm3_name1 AND ab3.matched_building_id IS NOT NULL) AS nb_airbnb_matched
    FROM public.houses_immat h
    JOIN public.cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL
      AND CAST(h.col67 AS float) < %s
      AND (h.col31 IS NULL OR h.col31 NOT IN %s)
    GROUP BY a.adm3_name1, a.adm2_name1, a.adm1_name, m.prix_m2_fcfa
    ORDER BY impot_estime_fcfa DESC;
""", (MAX_AREA, NON_BUILDING_TYPES))
print("tax_summary_communes recomputed")

conn.commit()

# Show results
cur.execute("SELECT name, nb_batiments, surface_totale_m2, impot_estime_fcfa, prix_mercurial_moyen FROM immatriculation.tax_summary_regions ORDER BY impot_estime_fcfa DESC;")
print("\n=== REGIONS (building tax only, area < 10,000 m², no farmland/forest/meadow) ===")
total_tax = 0
total_buildings = 0
for r in cur.fetchall():
    total_tax += r[3]
    total_buildings += r[1]
    print(f"  {r[0]:15s}: {r[1]:>10,} buildings  {r[2]:>15,} m²  {r[3]:>18,} FCFA  avg {r[4]:,} FCFA/m²")
print(f"\n  TOTAL: {total_buildings:,} buildings  {total_tax:,} FCFA ({total_tax/1e9:.1f} Md FCFA)")

cur.execute("SELECT name, region_name, nb_batiments, prix_m2_fcfa, impot_estime_fcfa FROM immatriculation.tax_summary_communes ORDER BY impot_estime_fcfa DESC LIMIT 15;")
print("\n=== TOP 15 COMMUNES ===")
for r in cur.fetchall():
    print(f"  {r[0]:20s} ({r[1]:15s}): {r[2]:>8,} buildings  {r[3]:>6,} FCFA/m²  {r[4]:>15,} FCFA")

cur.close()
conn.close()
print("\nDone!")
