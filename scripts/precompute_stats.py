"""
Pre-compute tax aggregations for the DGI dashboard.
Creates summary tables so the API doesn't need real-time spatial joins.

Run:  python precompute_stats.py
"""
import sys
import psycopg2

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # ── Step 1: Tag each building with its commune gid ────────
    print("Step 1: Adding commune_gid to houses_immat (if not exists)...")
    cur.execute("""
        DO $$ BEGIN
            ALTER TABLE houses_immat ADD COLUMN commune_gid INTEGER;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM houses_immat WHERE commune_gid IS NOT NULL;")
    already = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM houses_immat WHERE geom IS NOT NULL;")
    total = cur.fetchone()[0]
    print(f"  Already tagged: {already}/{total}")

    if already < total * 0.99:
        print("  Tagging buildings with commune_gid in chunks (this takes a few minutes)...")
        chunk_size = 100000
        for start in range(0, total, chunk_size):
            print(f"    Processing chunk {start:,} to {start+chunk_size:,}...")
            cur.execute("""
                UPDATE houses_immat h SET commune_gid = c.gid
                FROM cmr_admin3 c
                WHERE h.col0 IN (
                    SELECT col0 FROM houses_immat 
                    WHERE geom IS NOT NULL AND commune_gid IS NULL
                    LIMIT %s
                )
                AND ST_Contains(c.geom, ST_Centroid(h.geom));
            """, (chunk_size,))
            conn.commit()
            if cur.rowcount == 0:
                # No more buildings to tag
                break
        
        cur.execute("SELECT COUNT(*) FROM houses_immat WHERE commune_gid IS NOT NULL;")
        tagged = cur.fetchone()[0]
        print(f"  Tagged total: {tagged}/{total}")
    else:
        print("  Already mostly tagged, skipping.")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_houses_commune_gid ON houses_immat(commune_gid);")
    conn.commit()

    # ── Step 2: Create commune-level summary ──────────────────
    print("\nStep 2: Creating tax_summary_communes...")
    cur.execute("DROP TABLE IF EXISTS tax_summary_communes CASCADE;")
    cur.execute("""
        CREATE TABLE tax_summary_communes AS
        SELECT
            c.gid,
            COALESCE(c.adm3_name, c.adm3_name1) AS name,
            c.adm2_name1 AS dept_name,
            c.adm1_name AS region_name,
            c.adm3_pcode AS pcode,
            COALESCE(m.prix_m2_fcfa, 0) AS prix_mercurial,
            COUNT(h.col0) AS nb_batiments,
            ROUND(COALESCE(SUM(h.col67::numeric), 0), 0) AS surface_totale_m2,
            ROUND(COALESCE(SUM(h.col67::numeric * COALESCE(m.prix_m2_fcfa, 500)), 0), 0) AS impot_estime_fcfa,
            (SELECT COUNT(*) FROM airbnb_listings a WHERE ST_Contains(c.geom, a.geom)) AS nb_airbnb
        FROM cmr_admin3 c
        LEFT JOIN houses_immat h ON h.commune_gid = c.gid AND h.geom IS NOT NULL
        LEFT JOIN mercuriale_prix m ON LOWER(COALESCE(c.adm3_name, c.adm3_name1)) = LOWER(m.arrondissement)
        GROUP BY c.gid, c.adm3_name, c.adm3_name1, c.adm2_name1, c.adm1_name, c.adm3_pcode, m.prix_m2_fcfa;
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM tax_summary_communes;")
    print(f"  Created: {cur.fetchone()[0]} rows")

    # ── Step 3: Create department-level summary ───────────────
    print("\nStep 3: Creating tax_summary_departments...")
    cur.execute("DROP TABLE IF EXISTS tax_summary_departments CASCADE;")
    cur.execute("""
        CREATE TABLE tax_summary_departments AS
        SELECT
            d.gid,
            d.name,
            d.name_en,
            SUM(s.nb_batiments) AS nb_batiments,
            SUM(s.surface_totale_m2) AS surface_totale_m2,
            SUM(s.impot_estime_fcfa) AS impot_estime_fcfa,
            SUM(s.nb_airbnb) AS nb_airbnb
        FROM admin_departments d
        LEFT JOIN tax_summary_communes s
            ON ST_Contains(d.geom, ST_Centroid(
                (SELECT geom FROM cmr_admin3 WHERE gid = s.gid)
            ))
        GROUP BY d.gid, d.name, d.name_en;
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM tax_summary_departments;")
    print(f"  Created: {cur.fetchone()[0]} rows")

    # ── Step 4: Create region-level summary ───────────────────
    print("\nStep 4: Creating tax_summary_regions...")
    cur.execute("DROP TABLE IF EXISTS tax_summary_regions CASCADE;")
    cur.execute("""
        CREATE TABLE tax_summary_regions AS
        SELECT
            r.gid,
            r.name,
            r.name_en,
            COALESCE(SUM(s.nb_batiments), 0) AS nb_batiments,
            COALESCE(SUM(s.surface_totale_m2), 0) AS surface_totale_m2,
            COALESCE(SUM(s.impot_estime_fcfa), 0) AS impot_estime_fcfa,
            COALESCE(SUM(s.nb_airbnb), 0) AS nb_airbnb,
            (SELECT COUNT(*) FROM airbnb_listings a WHERE ST_Contains(r.geom, a.geom) AND a.matched_immat IS NOT NULL) AS nb_airbnb_matched
        FROM admin_regions r
        LEFT JOIN tax_summary_communes s
            ON ST_Contains(r.geom, ST_Centroid(
                (SELECT geom FROM cmr_admin3 WHERE gid = s.gid)
            ))
        GROUP BY r.gid, r.name, r.name_en, r.geom;
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM tax_summary_regions;")
    print(f"  Created: {cur.fetchone()[0]} rows")

    # ── Step 5: Show summary ──────────────────────────────────
    print("\n--- Summary ---")
    cur.execute("SELECT name, nb_batiments, impot_estime_fcfa FROM tax_summary_regions ORDER BY impot_estime_fcfa DESC;")
    print("\nRegions by tax potential:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} buildings, {row[2]:,.0f} FCFA")

    conn.commit()
    cur.close()
    conn.close()
    print("\nDone! Summary tables created successfully.")


if __name__ == "__main__":
    main()
