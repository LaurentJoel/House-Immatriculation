"""Calculate what tax totals look like with proper building-only filters."""
import psycopg2, psycopg2.extras

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Non-building land use types to exclude
NON_BUILDING_TYPES = (
    'farmland', 'forest', 'meadow', 'orchard', 'quarry', 'plant_nursery',
    'military', 'railway', 'cemetery', 'village_green', 'greenfield',
    'brownfield', 'grass', 'farmyard', 'allotments', 'basin',
    'recreation_ground', 'landfill', 'reservoir'
)

print("=== CURRENT TAX TOTAL (area < 500,000 m², no type filter) ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000;
""")
r = cur.fetchone()
print(f"  {r['cnt']:,} buildings  →  {r['total_tax']:,} FCFA")

# Scenario 1: Filter out non-building types
print("\n=== SCENARIO 1: Exclude non-building types (keep area < 500,000) ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
      AND (h.col31 IS NULL OR h.col31 NOT IN %s);
""", (NON_BUILDING_TYPES,))
r = cur.fetchone()
print(f"  {r['cnt']:,} buildings  →  {r['total_tax']:,} FCFA")

# Scenario 2: Filter types + cap area at 10,000 m²
print("\n=== SCENARIO 2: Exclude non-building types + area < 10,000 m² ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 10000
      AND (h.col31 IS NULL OR h.col31 NOT IN %s);
""", (NON_BUILDING_TYPES,))
r = cur.fetchone()
print(f"  {r['cnt']:,} buildings  →  {r['total_tax']:,} FCFA")

# Scenario 3: Filter types + cap area at 5,000 m²
print("\n=== SCENARIO 3: Exclude non-building types + area < 5,000 m² ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 5000
      AND (h.col31 IS NULL OR h.col31 NOT IN %s);
""", (NON_BUILDING_TYPES,))
r = cur.fetchone()
print(f"  {r['cnt']:,} buildings  →  {r['total_tax']:,} FCFA")

# Scenario 4: Scenario 2 + exclude negative OSM IDs
print("\n=== SCENARIO 4: Scenario 2 + positive OSM IDs only ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 10000
      AND (h.col31 IS NULL OR h.col31 NOT IN %s)
      AND CAST(h.col0 AS bigint) > 0;
""", (NON_BUILDING_TYPES,))
r = cur.fetchone()
print(f"  {r['cnt']:,} buildings  →  {r['total_tax']:,} FCFA")

# Breakdown by region with Scenario 2 filter
print("\n=== REGION COMPARISON: Current vs Filtered (Scenario 2) ===")
cur.execute("""
    SELECT a.adm1_name AS region,
           COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS current_tax,
           COUNT(*) FILTER (WHERE CAST(h.col67 AS float) < 10000
                           AND (h.col31 IS NULL OR h.col31 NOT IN ('farmland','forest','meadow','orchard','quarry','plant_nursery','military','railway','cemetery','village_green','greenfield','brownfield','grass','farmyard','allotments','basin','recreation_ground','landfill','reservoir'))) AS filtered_cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25) 
                 FILTER (WHERE CAST(h.col67 AS float) < 10000
                        AND (h.col31 IS NULL OR h.col31 NOT IN ('farmland','forest','meadow','orchard','quarry','plant_nursery','military','railway','cemetery','village_green','greenfield','brownfield','grass','farmyard','allotments','basin','recreation_ground','landfill','reservoir'))))::bigint AS filtered_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY a.adm1_name
    ORDER BY filtered_tax DESC;
""")
print(f"  {'Region':15s}  {'Current Count':>14s}  {'Current Tax':>22s}  {'Filtered Count':>14s}  {'Filtered Tax':>22s}  {'Reduction':>10s}")
for r in cur.fetchall():
    red = (1 - r['filtered_tax']/r['current_tax'])*100 if r['current_tax'] else 0
    print(f"  {r['region']:15s}  {r['cnt']:>14,}  {r['current_tax']:>22,}  {r['filtered_cnt']:>14,}  {r['filtered_tax']:>22,}  {red:>9.0f}%")

# What "residential" entries > 5000 m² look like
print("\n=== 'residential' entries > 5000 m² (suspicious) ===")
cur.execute("""
    SELECT COUNT(*) AS cnt, 
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           MIN(CAST(h.col67 AS float))::int AS min_area,
           MAX(CAST(h.col67 AS float))::int AS max_area
    FROM houses_immat h
    WHERE h.col31 = 'residential' AND h.col67 IS NOT NULL 
      AND CAST(h.col67 AS float) > 5000 AND CAST(h.col67 AS float) < 500000;
""")
r = cur.fetchone()
print(f"  Count: {r['cnt']:,}  avg: {r['avg_area']:,} m²  min: {r['min_area']:,} m²  max: {r['max_area']:,} m²")
print("  (These are likely residential LAND PARCELS, not individual buildings)")

cur.close()
conn.close()
