"""
Load the mercuriale des prix fonciers into PostgreSQL.
Source: F:\mercuriale_spm_foncier.json (Décret 2014/3211/PM)

Run:  python load_mercuriale.py
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

MERCURIALE_PATH = r"F:\mercuriale_spm_foncier.json"


def main():
    print(f"Reading {MERCURIALE_PATH} ...")
    with open(MERCURIALE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data["prix_minima_residentiel"]
    regles = data["regles"]
    decret = data["decret"]
    print(f"  Décret: {decret['numero']} du {decret['date']}")
    print(f"  {len(entries)} arrondissements")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Create table
        cur.execute("DROP TABLE IF EXISTS mercuriale_prix CASCADE;")
        cur.execute("""
            CREATE TABLE mercuriale_prix (
                id SERIAL PRIMARY KEY,
                region TEXT NOT NULL,
                departement TEXT NOT NULL,
                arrondissement TEXT NOT NULL,
                prix_m2_fcfa INTEGER NOT NULL,
                -- Usage multipliers (from the decree rules)
                mult_commercial NUMERIC DEFAULT 2.0,
                mult_industriel NUMERIC DEFAULT 0.5,
                mult_social NUMERIC DEFAULT 0.25,
                mult_cultuel NUMERIC DEFAULT 0.2,
                -- Annual redevance rates
                redevance_residentiel NUMERIC DEFAULT 0.25,
                redevance_commercial NUMERIC DEFAULT 0.50,
                redevance_industriel NUMERIC DEFAULT 0.10,
                redevance_agro NUMERIC DEFAULT 0.05,
                redevance_culturel NUMERIC DEFAULT 0.01
            );
        """)
        print("  Created table mercuriale_prix")

        # Insert data
        for entry in entries:
            cur.execute("""
                INSERT INTO mercuriale_prix (region, departement, arrondissement, prix_m2_fcfa)
                VALUES (%s, %s, %s, %s)
            """, (
                entry["region"],
                entry["departement"],
                entry["arrondissement"],
                entry["prix_m2_fcfa"],
            ))

        # Create indexes
        cur.execute("CREATE INDEX idx_mercuriale_region ON mercuriale_prix(region);")
        cur.execute("CREATE INDEX idx_mercuriale_arrondissement ON mercuriale_prix(arrondissement);")

        conn.commit()

        # Verify
        cur.execute("SELECT COUNT(*) FROM mercuriale_prix;")
        count = cur.fetchone()[0]
        print(f"  Inserted {count} rows")

        # Show price range
        cur.execute("SELECT MIN(prix_m2_fcfa), MAX(prix_m2_fcfa) FROM mercuriale_prix;")
        mn, mx = cur.fetchone()
        print(f"  Price range: {mn} - {mx} FCFA/m²")

        # Show top 5 most expensive
        cur.execute("""
            SELECT arrondissement, region, prix_m2_fcfa
            FROM mercuriale_prix
            ORDER BY prix_m2_fcfa DESC
            LIMIT 5;
        """)
        print("\n  Top 5 most expensive:")
        for row in cur.fetchall():
            print(f"    {row[0]} ({row[1]}): {row[2]:,} FCFA/m²")

        print("\n✅ Mercuriale loaded successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
