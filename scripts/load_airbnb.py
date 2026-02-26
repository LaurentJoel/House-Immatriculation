"""
Load Airbnb listings into PostgreSQL and perform spatial matching
with immatriculated buildings.

Run:  python load_airbnb.py
"""
import csv
import json
import sys
import psycopg2

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

AIRBNB_PATH = r"F:\airbnb_data"

# Column positions (headerless CSV with embedded JSON blob)
COL_ID = 0
COL_TITLE = 1
COL_DESC = 2
COL_LAT = 11
COL_LON = 12
COL_URL = 13


def parse_airbnb_csv(filepath):
    """Parse the headerless Airbnb CSV file."""
    print(f"Reading {filepath} ...")
    listings = []

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader, 1):
            if len(row) < 14:
                continue
            try:
                lat_str = row[COL_LAT].strip()
                lon_str = row[COL_LON].strip()
                if not lat_str or not lon_str:
                    continue
                lat = float(lat_str)
                lon = float(lon_str)
                # Validate coordinates are in Cameroon area
                if not (1.5 < lat < 13.5 and 8.0 < lon < 16.5):
                    continue
                listing = {
                    "ext_id": row[COL_ID].strip(),
                    "title": row[COL_TITLE].strip()[:500],
                    "description": row[COL_DESC].strip()[:2000],
                    "lat": lat,
                    "lon": lon,
                    "url": row[COL_URL].strip()[:500],
                }
                listings.append(listing)
            except (ValueError, IndexError):
                continue

    print(f"  Parsed {len(listings)} listings with valid Cameroon coordinates")
    return listings


def main():
    listings = parse_airbnb_csv(AIRBNB_PATH)

    if not listings:
        print("No listings found!")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Create table
        cur.execute("DROP TABLE IF EXISTS airbnb_listings CASCADE;")
        cur.execute("""
            CREATE TABLE airbnb_listings (
                id SERIAL PRIMARY KEY,
                ext_id TEXT,
                title TEXT,
                description TEXT,
                lat DOUBLE PRECISION,
                lon DOUBLE PRECISION,
                url TEXT,
                geom GEOMETRY(Point, 4326),
                -- Filled by spatial matching
                matched_building_id TEXT,
                matched_immat TEXT,
                match_distance_m DOUBLE PRECISION,
                matched_commune TEXT,
                matched_departement TEXT,
                matched_region TEXT
            );
        """)
        print("  Created table airbnb_listings")

        # Insert listings
        for listing in listings:
            cur.execute("""
                INSERT INTO airbnb_listings (ext_id, title, description, lat, lon, url, geom)
                VALUES (%s, %s, %s, %s, %s, %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            """, (
                listing["ext_id"],
                listing["title"],
                listing["description"],
                listing["lat"],
                listing["lon"],
                listing["url"],
                listing["lon"],  # MakePoint takes (lon, lat)
                listing["lat"],
            ))

        cur.execute("CREATE INDEX idx_airbnb_geom ON airbnb_listings USING GIST(geom);")
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM airbnb_listings;")
        count = cur.fetchone()[0]
        print(f"  Inserted {count} Airbnb listings")

        # --- Match with admin boundaries first (fast) ---
        print("\n--- Matching Airbnb -> admin boundaries ---")
        cur.execute("""
            UPDATE airbnb_listings a SET
                matched_commune = c.adm3_name,
                matched_departement = c.adm2_name1,
                matched_region = c.adm1_name
            FROM cmr_admin3 c
            WHERE ST_Contains(c.geom, a.geom);
        """)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM airbnb_listings WHERE matched_region IS NOT NULL;")
        admin_matched = cur.fetchone()[0]
        print(f"  Matched {admin_matched}/{count} listings to admin boundaries")

        # Show distribution by region
        cur.execute("""
            SELECT COALESCE(matched_region, 'UNMATCHED') AS region, COUNT(*) as cnt
            FROM airbnb_listings
            GROUP BY matched_region
            ORDER BY cnt DESC;
        """)
        print("\n  Distribution by region:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1]} listings")

        # --- Spatial matching: find nearest building for each Airbnb ---
        print("\n--- Spatial matching: Airbnb -> nearest building ---")
        print("  (This may take a few minutes with ~2M buildings...)")
        cur.execute("""
            UPDATE airbnb_listings a SET
                matched_building_id = sub.building_id,
                matched_immat = sub.immat,
                match_distance_m = sub.dist_m
            FROM (
                SELECT DISTINCT ON (a2.id)
                    a2.id AS airbnb_id,
                    h.col0::text AS building_id,
                    h.col69 AS immat,
                    ST_Distance(a2.geom::geography, h.geom::geography) AS dist_m
                FROM airbnb_listings a2
                CROSS JOIN LATERAL (
                    SELECT col0, col69, geom
                    FROM houses_immat
                    WHERE geom IS NOT NULL
                    ORDER BY a2.geom <-> geom
                    LIMIT 1
                ) h
            ) sub
            WHERE a.id = sub.airbnb_id;
        """)
        conn.commit()

        # Check results
        cur.execute("SELECT COUNT(*) FROM airbnb_listings WHERE matched_immat IS NOT NULL;")
        matched = cur.fetchone()[0]
        print(f"  Matched {matched}/{count} listings to nearest building")

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE match_distance_m < 50) AS close,
                COUNT(*) FILTER (WHERE match_distance_m >= 50 AND match_distance_m < 200) AS medium,
                COUNT(*) FILTER (WHERE match_distance_m >= 200) AS far
            FROM airbnb_listings
            WHERE matched_immat IS NOT NULL;
        """)
        row = cur.fetchone()
        print(f"  Close (<50m): {row[0]}, Medium (50-200m): {row[1]}, Far (>200m): {row[2]}")

        # Show a few sample matches
        cur.execute("""
            SELECT title, matched_immat, ROUND(match_distance_m::numeric, 1) AS dist_m, matched_commune
            FROM airbnb_listings
            WHERE matched_immat IS NOT NULL
            ORDER BY match_distance_m
            LIMIT 5;
        """)
        print("\n  Top 5 closest matches:")
        for row in cur.fetchall():
            print(f"    {row[0][:40]}... -> {row[1]} ({row[2]}m) in {row[3]}")

        print("\nDone! Airbnb data loaded and matched successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
