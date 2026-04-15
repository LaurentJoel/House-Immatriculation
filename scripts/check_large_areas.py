"""Investigate large-area entries in tax calculations to find non-building spaces."""
import psycopg2, psycopg2.extras

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Area distribution buckets
print("=== AREA DISTRIBUTION (buildings with mercuriale price) ===")
cur.execute("""
    SELECT 
        CASE 
            WHEN CAST(h.col67 AS float) < 50 THEN '< 50 m²'
            WHEN CAST(h.col67 AS float) < 200 THEN '50-200 m²'
            WHEN CAST(h.col67 AS float) < 500 THEN '200-500 m²'
            WHEN CAST(h.col67 AS float) < 1000 THEN '500-1000 m²'
            WHEN CAST(h.col67 AS float) < 5000 THEN '1000-5000 m²'
            WHEN CAST(h.col67 AS float) < 10000 THEN '5000-10000 m²'
            WHEN CAST(h.col67 AS float) < 50000 THEN '10000-50000 m²'
            WHEN CAST(h.col67 AS float) < 100000 THEN '50000-100000 m²'
            ELSE '100000-500000 m²'
        END AS area_bucket,
        COUNT(*) AS count,
        ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY area_bucket
    ORDER BY MIN(CAST(h.col67 AS float));
""")
for r in cur.fetchall():
    print(f"  {r['area_bucket']:20s}  count={r['count']:>10,}  tax={r['total_tax']:>20,} FCFA")

# 2. What are the very large entries (>5000 m²)? Real buildings or not?
print("\n=== SAMPLE LARGE ENTRIES > 5000 m² ===")
cur.execute("""
    SELECT h.col0, h.col31 AS building_type, h.col8 AS amenity, h.col12 AS name,
           CAST(h.col67 AS float) AS area, h.col69 AS immat,
           a.adm3_name1 AS commune,
           ROUND(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25)::bigint AS tax_est
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 5000
      AND CAST(h.col67 AS float) < 500000
    ORDER BY CAST(h.col67 AS float) DESC
    LIMIT 30;
""")
for r in cur.fetchall():
    print(f"  id={r['col0']}  area={r['area']:>10,.0f}m²  type={str(r['building_type'] or '-'):15s}  amenity={str(r['amenity'] or '-'):15s}  name={str(r['name'] or '-')[:30]:30s}  commune={r['commune']}  tax={r['tax_est']:>15,}")

# 3. Count and tax contribution of entries > 1000 m²
print("\n=== TAX CONTRIBUTION BY SIZE ===")
cur.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE CAST(h.col67 AS float) <= 1000) AS cnt_normal,
        COUNT(*) FILTER (WHERE CAST(h.col67 AS float) > 1000) AS cnt_large,
        ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25) 
              FILTER (WHERE CAST(h.col67 AS float) <= 1000))::bigint AS tax_normal,
        ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25) 
              FILTER (WHERE CAST(h.col67 AS float) > 1000))::bigint AS tax_large,
        ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS tax_total
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000;
""")
r = cur.fetchone()
print(f"  Buildings ≤1000m²: {r['cnt_normal']:>10,}  tax: {r['tax_normal']:>20,} FCFA")
print(f"  Buildings >1000m²: {r['cnt_large']:>10,}  tax: {r['tax_large']:>20,} FCFA")
print(f"  Total:             {r['cnt_normal']+r['cnt_large']:>10,}  tax: {r['tax_total']:>20,} FCFA")
pct = r['tax_large'] * 100 / r['tax_total'] if r['tax_total'] else 0
print(f"  Large entries are {r['cnt_large']*100/(r['cnt_normal']+r['cnt_large']):.1f}% of count but {pct:.1f}% of tax")

# 4. What types do large entries have?
print("\n=== BUILDING TYPES FOR ENTRIES > 1000 m² ===")
cur.execute("""
    SELECT COALESCE(h.col31, 'NULL') AS building_type, 
           COUNT(*) AS cnt,
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 1000
      AND CAST(h.col67 AS float) < 500000
    GROUP BY COALESCE(h.col31, 'NULL')
    ORDER BY total_tax DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  {r['building_type']:20s}  count={r['cnt']:>8,}  avg_area={r['avg_area']:>8,}m²  tax={r['total_tax']:>18,} FCFA")

# 5. Check OSM IDs - negative = imported boundaries
print("\n=== NEGATIVE OSM IDs (boundary polygons) with area > 1000 m² ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 1000
      AND CAST(h.col67 AS float) < 500000
      AND CAST(h.col0 AS bigint) < 0;
""")
r = cur.fetchone()
print(f"  Negative ID entries >1000m²: count={r['cnt']:,}  tax={r['total_tax']:,} FCFA")

# 6. What about col8 (amenity) - schools, hospitals, etc?
print("\n=== NON-RESIDENTIAL AMENITIES in tax calculation ===")
cur.execute("""
    SELECT COALESCE(h.col8, 'NULL') AS amenity, 
           COUNT(*) AS cnt,
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           ROUND(SUM(CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25))::bigint AS total_tax
    FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
      AND h.col8 IS NOT NULL
    GROUP BY COALESCE(h.col8, 'NULL')
    ORDER BY total_tax DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  {r['amenity']:25s}  count={r['cnt']:>8,}  avg_area={r['avg_area']:>8,}m²  tax={r['total_tax']:>18,} FCFA")

cur.close()
conn.close()
