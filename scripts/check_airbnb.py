import psycopg2
conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

# Schema
print("=== airbnb_listings columns ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='airbnb_listings' AND table_schema='immatriculation' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]}")

# Sample rows
print("\n=== Sample airbnb rows ===")
cur.execute("SELECT * FROM immatriculation.airbnb_listings LIMIT 3")
cols = [d[0] for d in cur.description]
print("Columns:", cols)
for row in cur.fetchall():
    print(dict(zip(cols, row)))

# Check how many have matched_building_id
print("\n=== Match stats ===")
cur.execute("SELECT COUNT(*) FROM immatriculation.airbnb_listings")
print(f"Total: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM immatriculation.airbnb_listings WHERE matched_building_id IS NOT NULL")
print(f"With matched_building_id: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM immatriculation.airbnb_listings WHERE matched_immat IS NOT NULL AND matched_immat != ''")
print(f"With matched_immat: {cur.fetchone()[0]}")

# Check if matched_building_id links to houses_immat
print("\n=== Can we join to houses_immat? ===")
cur.execute("""
    SELECT ab.id, ab.title, ab.matched_building_id, ab.matched_immat, ab.match_distance_m,
           h.col0, h.col67, h.col69
    FROM immatriculation.airbnb_listings ab
    LEFT JOIN houses_immat h ON ab.matched_building_id = h.col0
    WHERE ab.matched_building_id IS NOT NULL
    LIMIT 5
""")
cols2 = [d[0] for d in cur.description]
for row in cur.fetchall():
    print(dict(zip(cols2, row)))

conn.close()
