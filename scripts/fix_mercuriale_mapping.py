"""
Create a commune name alias table mapping admin commune names to mercuriale commune names,
handling Yaoundé 1-7 → Yaoundé, Douala 1-6 → Douala, accent differences, etc.
Then update the server SQL to use this mapping for tax lookups.
"""
import psycopg2
import unicodedata
import re

conn = psycopg2.connect(host='localhost', port=5433, dbname='immatriculation',
                        user='immat_user', password='immat_dev_password')
cur = conn.cursor()

# Get all mercuriale names
cur.execute("SELECT commune_name, prix_m2_fcfa FROM immatriculation.mercuriale_lookup")
merc_rows = cur.fetchall()
merc_names = {r[0]: r[1] for r in merc_rows}
print(f"Mercuriale: {len(merc_names)} entries")

# Get all admin commune names
cur.execute("SELECT DISTINCT adm3_name1 FROM cmr_admin3 WHERE adm3_name1 IS NOT NULL")
admin_names = [r[0] for r in cur.fetchall()]
print(f"Admin communes: {len(admin_names)}")

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def normalize(s):
    return strip_accents(s.strip()).lower()

# Build mapping: admin_name → mercuriale_name
mapping = {}

# Step 1: exact match (case-insensitive)
for admin in admin_names:
    for merc in merc_names:
        if admin.lower() == merc.lower():
            mapping[admin] = merc
            break

# Step 2: accent-stripped match
unmatched = [a for a in admin_names if a not in mapping]
for admin in unmatched:
    na = normalize(admin)
    for merc in merc_names:
        if normalize(merc) == na:
            mapping[admin] = merc
            break

# Step 3: Yaoundé arrondissements → Yaoundé
unmatched = [a for a in admin_names if a not in mapping]
for admin in unmatched:
    na = normalize(admin)
    if na.startswith('yaounde'):
        mapping[admin] = 'Yaoundé'
    elif na.startswith('douala') and 'manoka' not in na:
        mapping[admin] = 'Douala I, II, III, IV, V'
    elif na.startswith('douala') and 'manoka' in na:
        mapping[admin] = 'Douala VI (Manoka)'

# Step 4: Bafoussam arrondissements → Bafoussam, Bertoua arrondissements, Bamenda arrondissements, etc.
city_map = {
    'bafoussam': 'Bafoussam',
    'bamenda': 'Bamenda',
    'bertoua': 'Bertoua',
    'edea': 'Edéa',
    'ebolowa': 'Ebolowa',
    'garoua': 'Garoua',
    'kribi': 'Kribi',
    'kumba': 'Kumba',
    'limbe': 'Limbé',
    'maroua': 'Maroua',
    'nkongsamba': 'Nkongsamba',
    'ngaoundere': 'Ngaoundéré',
    'nanga-eboko': 'Nanga-Eboko',
    'sangmelima': 'Sangmélima',
    'foumban': 'Foumban',
    'foumbot': 'Foumbot',
    'kumbo': 'Kumbo',
    'garoua-boulai': 'Garoua-Boulaï',
    'meiganga': 'Meiganga',
    'mora': 'Mora',
    'mokolo': 'Mokolo',
    'kousseri': 'Kousseri',
}

unmatched = [a for a in admin_names if a not in mapping]
for admin in unmatched:
    na = normalize(admin)
    # Strip ordinal suffixes: "1er", "2e", "3e", "1st", "2nd", "3rd", etc.
    base = re.sub(r'\s+\d+(er|e|st|nd|rd|th)$', '', na)
    for city_norm, city_merc in city_map.items():
        if base == city_norm and city_merc in merc_names:
            mapping[admin] = city_merc
            break

# Step 5: fuzzy fallback - try stripping accents and common suffixes
unmatched = [a for a in admin_names if a not in mapping]
for admin in unmatched:
    na = normalize(admin)
    # Try removing trailing digits/ordinals
    base = re.sub(r'\s+\d+(er|e|st|nd|rd|th)?$', '', na)
    for merc in merc_names:
        if normalize(merc) == base:
            mapping[admin] = merc
            break

# Final: still unmatched
unmatched = [a for a in admin_names if a not in mapping]

print(f"\nMatched: {len(mapping)}")
print(f"Still unmatched: {len(unmatched)}")
if unmatched:
    for u in sorted(unmatched)[:30]:
        print(f"  {u}")
    if len(unmatched) > 30:
        print(f"  ... and {len(unmatched)-30} more")

# Create the mapping table
print("\nCreating immatriculation.commune_name_alias table...")
cur.execute("DROP TABLE IF EXISTS immatriculation.commune_name_alias")
cur.execute("""
    CREATE TABLE immatriculation.commune_name_alias (
        admin_name TEXT PRIMARY KEY,
        mercuriale_name TEXT NOT NULL
    )
""")
for admin, merc in mapping.items():
    cur.execute("INSERT INTO immatriculation.commune_name_alias (admin_name, mercuriale_name) VALUES (%s, %s)",
                (admin, merc))
print(f"Inserted {len(mapping)} mappings")

conn.commit()

# Verify: how many buildings now get a mercuriale price?
cur.execute("""
    SELECT COUNT(*) FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.commune_name_alias ca ON a.adm3_name1 = ca.admin_name
    JOIN immatriculation.mercuriale_lookup m ON ca.mercuriale_name = m.commune_name
""")
print(f"\nBuildings with mercuriale via alias: {cur.fetchone()[0]:,}")

# Old way (direct match)
cur.execute("""
    SELECT COUNT(*) FROM houses_immat h
    JOIN cmr_admin3 a ON h.commune_gid = a.gid
    JOIN immatriculation.mercuriale_lookup m ON lower(a.adm3_name1) = lower(m.commune_name)
""")
print(f"Buildings with mercuriale (old direct): {cur.fetchone()[0]:,}")

conn.close()
print("Done!")
