import urllib.request, json

# Small area in central Yaoundé with many small buildings
r = urllib.request.urlopen('http://localhost:5558/api/houses?west=11.505&south=3.865&east=11.515&north=3.875&limit=50')
d = json.loads(r.read())
print(f"=== SMALL AREA IN YAOUNDE CENTER ({d['total_in_view']} returned) ===")
with_tax = 0
for f in d['features']:
    p = f['properties']
    bt = p.get('building_type') or '-'
    area = p.get('area')
    tax = p.get('impot_estime')
    if tax:
        with_tax += 1
    try:
        a = float(area) if area else 0
    except:
        a = 0
    if a < 500:  # Show small buildings
        print(f"  type={bt:15s}  area={str(area):>8s}  tax={str(tax):>12s}  immat={p.get('immatriculation','')[:20]}")

print(f"\n  With tax: {with_tax}/{d['total_in_view']}")

# Also check farmland explicitly gets no tax
farmland_taxed = sum(1 for f in d['features'] 
                     if f['properties'].get('building_type') == 'farmland' 
                     and f['properties'].get('impot_estime'))
farmland_total = sum(1 for f in d['features'] 
                     if f['properties'].get('building_type') == 'farmland')
print(f"  Farmland with tax: {farmland_taxed}/{farmland_total}")

# Check large area entries
large_taxed = sum(1 for f in d['features']
                  if f['properties'].get('area') and float(f['properties']['area']) > 10000
                  and f['properties'].get('impot_estime'))
large_total = sum(1 for f in d['features']
                  if f['properties'].get('area') and float(f['properties']['area']) > 10000)
print(f"  Large (>10000m²) with tax: {large_taxed}/{large_total}")
