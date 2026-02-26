"""
Load OSMB GeoJSON administrative boundaries into PostgreSQL.
Creates admin_regions (Level 4) and admin_departments (Level 6),
and enriches cmr_admin3 with names from Level 8.

Run:  python load_osmb_admin.py
"""
import json
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

GEOJSON_PATH = r"F:\OSMB-38c190a8713d77f649f63dbfc466b904a47001d2Cameroon.geojson"


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def load_geojson():
    print(f"Reading {GEOJSON_PATH} ...")
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data["features"]
    print(f"  Total features: {len(features)}")
    return features


def create_tables(cur):
    """Create admin_regions and admin_departments tables."""
    cur.execute("DROP TABLE IF EXISTS admin_regions CASCADE;")
    cur.execute("DROP TABLE IF EXISTS admin_departments CASCADE;")

    cur.execute("""
        CREATE TABLE admin_regions (
            gid SERIAL PRIMARY KEY,
            osm_id BIGINT,
            name TEXT,
            name_en TEXT,
            admin_level INTEGER,
            parent_ids BIGINT[],
            center_lat DOUBLE PRECISION,
            center_lon DOUBLE PRECISION,
            geom GEOMETRY(MultiPolygon, 4326)
        );
    """)

    cur.execute("""
        CREATE TABLE admin_departments (
            gid SERIAL PRIMARY KEY,
            osm_id BIGINT,
            name TEXT,
            name_en TEXT,
            admin_level INTEGER,
            parent_ids BIGINT[],
            center_lat DOUBLE PRECISION,
            center_lon DOUBLE PRECISION,
            geom GEOMETRY(MultiPolygon, 4326)
        );
    """)
    print("  Created tables admin_regions and admin_departments")


def insert_feature(cur, table, feat):
    """Insert a single GeoJSON feature into the specified table."""
    props = feat["properties"]
    geom_json = json.dumps(feat["geometry"])
    parent_ids = props.get("parents_administrative") or props.get("parents") or []

    cur.execute(f"""
        INSERT INTO {table} (osm_id, name, name_en, admin_level, parent_ids,
                             center_lat, center_lon, geom)
        VALUES (%s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
    """, (
        props.get("osm_id"),
        props.get("name"),
        props.get("name_en"),
        props.get("admin_level"),
        parent_ids,
        props.get("admin_centre_node_lat"),
        props.get("admin_centre_node_lng"),
        geom_json,
    ))


def enrich_cmr_admin3(cur, communes):
    """
    Use Level 8 features to fill in missing adm3_name and adm2_name
    in the existing cmr_admin3 table.
    """
    print(f"\n--- Enriching cmr_admin3 with {len(communes)} Level 8 communes ---")

    # Check which columns are empty
    cur.execute("SELECT COUNT(*) FROM cmr_admin3 WHERE adm3_name IS NOT NULL AND adm3_name != '';")
    filled = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cmr_admin3;")
    total = cur.fetchone()[0]
    print(f"  cmr_admin3: {filled}/{total} rows have adm3_name filled")

    updated = 0
    for feat in communes:
        props = feat["properties"]
        name = props.get("name")
        if not name:
            continue
        geom_json = json.dumps(feat["geometry"])

        # Match by spatial intersection of centroids
        cur.execute("""
            UPDATE cmr_admin3 SET adm3_name = %s
            WHERE (adm3_name IS NULL OR adm3_name = '')
              AND ST_Intersects(
                  ST_Centroid(geom),
                  ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
              );
        """, (name, geom_json))
        updated += cur.rowcount

    print(f"  Updated {updated} rows in cmr_admin3.adm3_name")

    # Verify
    cur.execute("SELECT COUNT(*) FROM cmr_admin3 WHERE adm3_name IS NOT NULL AND adm3_name != '';")
    now_filled = cur.fetchone()[0]
    print(f"  cmr_admin3: {now_filled}/{total} rows now have adm3_name filled")


def create_indexes(cur):
    """Create spatial indexes for fast querying."""
    print("\n--- Creating spatial indexes ---")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_regions_geom ON admin_regions USING GIST(geom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_departments_geom ON admin_departments USING GIST(geom);")
    print("  Done")


def main():
    features = load_geojson()

    # Group features by admin level
    by_level = {}
    for feat in features:
        lvl = feat["properties"].get("admin_level")
        by_level.setdefault(lvl, []).append(feat)

    print("\nFeatures by level:")
    for lvl, feats in sorted(by_level.items(), key=lambda x: x[0]):
        print(f"  Level {lvl}: {len(feats)}")

    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Create tables
        create_tables(cur)

        # Insert regions (Level 4)
        regions = by_level.get(4, [])
        print(f"\n--- Inserting {len(regions)} regions ---")
        for feat in regions:
            insert_feature(cur, "admin_regions", feat)
        print(f"  Inserted {len(regions)} regions")

        # Insert departments (Level 6)
        departments = by_level.get(6, [])
        print(f"\n--- Inserting {len(departments)} departments ---")
        for feat in departments:
            insert_feature(cur, "admin_departments", feat)
        print(f"  Inserted {len(departments)} departments")

        # Enrich cmr_admin3 with Level 8 data
        communes = by_level.get(8, [])
        enrich_cmr_admin3(cur, communes)

        # Create indexes
        create_indexes(cur)

        conn.commit()
        print("\n✅ All admin data loaded successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
