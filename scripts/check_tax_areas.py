"""Analyze what's being included in tax calculations — check for non-building large areas."""
import psycopg2, psycopg2.extras

conn = psycopg2.connect(host="localhost", port=5433, dbname="immatriculation",
                        user="immat_user", password="immat_dev_password")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Overall area distribution of houses with tax (area < 500000 filter)
print("=== AREA DISTRIBUTION (all buildings with area < 500,000) ===")
cur.execute("""
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN CAST(h.col67 AS float) < 50 THEN 1 END) AS under_50m2,
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 50 AND 200 THEN 1 END) AS "50_200m2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 200 AND 500 THEN 1 END) AS "200_500m2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 500 AND 1000 THEN 1 END) AS "500_1000m2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 1000 AND 5000 THEN 1 END) AS "1k_5km2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 5000 AND 10000 THEN 1 END) AS "5k_10km2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 10000 AND 50000 THEN 1 END) AS "10k_50km2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 50000 AND 100000 THEN 1 END) AS "50k_100km2",
        COUNT(CASE WHEN CAST(h.col67 AS float) BETWEEN 100000 AND 500000 THEN 1 END) AS "100k_500km2"
    FROM houses_immat h
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
""")
r = cur.fetchone()
for k, v in r.items():
    print(f"  {k}: {v:,}")

# 2. What types of features are in the large area ranges (> 1000 m²)?
print("\n=== BUILDING TYPES for area > 1000 m² (sample) ===")
cur.execute("""
    SELECT h.col31 AS building_type, COUNT(*) AS cnt,
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           ROUND(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25))::bigint AS tax_contribution
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) BETWEEN 1000 AND 500000
    GROUP BY h.col31
    ORDER BY tax_contribution DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  {str(r['building_type'] or 'NULL'):25s}  count={r['cnt']:>8,}  avg_area={r['avg_area']:>8,} m²  tax={r['tax_contribution']:>15,} FCFA")

# 3. What types for area > 5000 m²?
print("\n=== BUILDING TYPES for area > 5,000 m² ===")
cur.execute("""
    SELECT h.col31 AS building_type, COUNT(*) AS cnt,
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           MAX(CAST(h.col67 AS float))::int AS max_area,
           ROUND(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25))::bigint AS tax_contribution
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 5000
      AND CAST(h.col67 AS float) < 500000
    GROUP BY h.col31
    ORDER BY tax_contribution DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  {str(r['building_type'] or 'NULL'):25s}  count={r['cnt']:>8,}  avg={r['avg_area']:>8,} m²  max={r['max_area']:>8,} m²  tax={r['tax_contribution']:>15,} FCFA")

# 4. Check col8 (amenity) for large entries — are they schools, hospitals, etc?
print("\n=== AMENITY TAGS for area > 5,000 m² ===")
cur.execute("""
    SELECT h.col8 AS amenity, COUNT(*) AS cnt,
           ROUND(AVG(CAST(h.col67 AS float)))::int AS avg_area,
           ROUND(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25))::bigint AS tax_contribution
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) > 5000
      AND CAST(h.col67 AS float) < 500000
    GROUP BY h.col8
    ORDER BY tax_contribution DESC
    LIMIT 20;
""")
for r in cur.fetchall():
    print(f"  {str(r['amenity'] or 'NULL'):25s}  count={r['cnt']:>8,}  avg={r['avg_area']:>8,} m²  tax={r['tax_contribution']:>15,} FCFA")

# 5. Tax contribution by area bucket
print("\n=== TAX CONTRIBUTION BY AREA BUCKET ===")
cur.execute("""
    SELECT 
        CASE 
            WHEN CAST(h.col67 AS float) < 50 THEN '< 50 m²'
            WHEN CAST(h.col67 AS float) < 200 THEN '50-200 m²'
            WHEN CAST(h.col67 AS float) < 500 THEN '200-500 m²'
            WHEN CAST(h.col67 AS float) < 1000 THEN '500-1000 m²'
            WHEN CAST(h.col67 AS float) < 5000 THEN '1k-5k m²'
            WHEN CAST(h.col67 AS float) < 10000 THEN '5k-10k m²'
            WHEN CAST(h.col67 AS float) < 50000 THEN '10k-50k m²'
            WHEN CAST(h.col67 AS float) < 100000 THEN '50k-100k m²'
            ELSE '100k-500k m²'
        END AS bucket,
        COUNT(*) AS cnt,
        ROUND(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25))::bigint AS tax_total,
        ROUND(100.0 * SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25) / 
            NULLIF((SELECT SUM(CAST(h2.col67 AS float) * COALESCE(m2.prix_m2_fcfa, 0) * 0.25) 
             FROM houses_immat h2 
             LEFT JOIN cmr_admin3 a2 ON h2.commune_gid = a2.gid 
             LEFT JOIN immatriculation.commune_name_alias ca2 ON a2.adm3_name1 = ca2.admin_name
             LEFT JOIN immatriculation.mercuriale_lookup m2 ON ca2.mercuriale_name = m2.commune_name
             WHERE h2.col67 IS NOT NULL AND CAST(h2.col67 AS float) < 500000), 0), 1)::float AS pct
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
    GROUP BY bucket
    ORDER BY MIN(CAST(h.col67 AS float));
""")
total_tax = 0
for r in cur.fetchall():
    total_tax += r['tax_total'] or 0
    print(f"  {r['bucket']:15s}  {r['cnt']:>10,} entries  tax={r['tax_total']:>18,} FCFA  ({r['pct']:.1f}%)")
print(f"  {'TOTAL':15s}  tax={total_tax:>18,} FCFA")

# 6. Sample of very large entries (area > 50,000 m²) — what are they?
print("\n=== SAMPLE: entries with area 50,000 - 500,000 m² ===")
cur.execute("""
    SELECT h.col0, h.col31 AS building_type, h.col8 AS amenity, h.col12 AS name,
           CAST(h.col67 AS float)::int AS area, h.col69 AS immat,
           a.adm3_name1 AS commune, m.prix_m2_fcfa,
           ROUND(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25)::bigint AS tax
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) BETWEEN 50000 AND 500000
    ORDER BY CAST(h.col67 AS float) DESC
    LIMIT 25;
""")
for r in cur.fetchall():
    print(f"  id={r['col0']}  area={r['area']:>8,} m²  type={str(r['building_type'] or '-'):15s}  amenity={str(r['amenity'] or '-'):15s}  name={str(r['name'] or '-')[:30]:30s}  commune={r['commune']}  tax={r['tax']:>12,}")

# 7. Check OSM IDs — negative IDs are often boundaries/relations
print("\n=== NEGATIVE OSM IDs (boundaries imported as buildings) ===")
cur.execute("""
    SELECT COUNT(*) AS total_negative,
           COUNT(CASE WHEN CAST(h.col67 AS float) > 5000 THEN 1 END) AS neg_gt_5k,
           COUNT(CASE WHEN CAST(h.col67 AS float) > 10000 THEN 1 END) AS neg_gt_10k,
           COUNT(CASE WHEN CAST(h.col67 AS float) > 50000 THEN 1 END) AS neg_gt_50k,
           ROUND(SUM(CASE WHEN m.prix_m2_fcfa IS NOT NULL 
                      THEN CAST(h.col67 AS float) * m.prix_m2_fcfa * 0.25 ELSE 0 END))::bigint AS neg_tax_total
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col0 < 0 AND h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 500000
""")
r = cur.fetchone()
for k, v in r.items():
    print(f"  {k}: {v:,}" if isinstance(v, int) else f"  {k}: {v}")

# 8. Total tax from realistic buildings only (area < 1000 m², typical houses)
print("\n=== REALISTIC BUILDING TAX (area < 1000 m² = typical houses) ===")
cur.execute("""
    SELECT COUNT(*) AS cnt,
           ROUND(SUM(CAST(h.col67 AS float) * COALESCE(m.prix_m2_fcfa, 0) * 0.25))::bigint AS tax_total
    FROM houses_immat h
    LEFT JOIN cmr_admin3 a ON h.commune_gid = a.gid
    LEFT JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    LEFT JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
    WHERE h.col67 IS NOT NULL AND CAST(h.col67 AS float) < 1000
""")
r = cur.fetchone()
print(f"  Buildings: {r['cnt']:,}  Tax: {r['tax_total']:,} FCFA")

cur.close()
conn.close()
