import urllib.request, json

# Test tax summary
r = urllib.request.urlopen('http://localhost:5558/api/tax-summary')
d = json.loads(r.read())
print("=== TAX SUMMARY REGIONS ===")
for x in d['data']:
    print(f"  {x['name']:15s} {x['nb_batiments']:>10,} buildings  {x['impot_estime_fcfa']:>18,.0f} FCFA")

# Test a house in Yaoundé to check per-building tax
r2 = urllib.request.urlopen('http://localhost:5558/api/houses?west=11.49&south=3.85&east=11.53&north=3.88&limit=20')
d2 = json.loads(r2.read())
print(f"\n=== SAMPLE HOUSES IN YAOUNDE ({d2['total_in_view']} returned) ===")
with_tax = 0
no_tax = 0
for f in d2['features'][:10]:
    p = f['properties']
    bt = p.get('building_type') or '-'
    area = p.get('area') or '?'
    tax = p.get('impot_estime')
    if tax:
        with_tax += 1
    else:
        no_tax += 1
    print(f"  type={bt:15s}  area={str(area):>8s}  tax={str(tax):>10s}  commune={p.get('commune','-')}")

total_with = sum(1 for f in d2['features'] if f['properties'].get('impot_estime'))
total_wo = len(d2['features']) - total_with
print(f"\n  With tax: {total_with}  Without: {total_wo} (of {len(d2['features'])})")
