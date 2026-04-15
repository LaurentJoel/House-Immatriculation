import urllib.request, json

r = urllib.request.urlopen('http://localhost:5558/api/airbnb?bbox=11.4,3.8,11.6,3.95')
d = json.loads(r.read())
print(f'Features: {len(d["features"])}')
for f in d['features'][:5]:
    p = f['properties']
    t = (p.get("title") or "?")[:40]
    bt = p.get("building_type") or "-"
    pm = p.get("prix_m2")
    ie = p.get("impot_estime")
    cm = p.get("commune") or "-"
    print(f'  {t:40s} type={bt:12s} prix={pm} tax={ie} commune={cm}')

with_tax = sum(1 for f in d['features'] if f['properties']['impot_estime'])
with_type = sum(1 for f in d['features'] if f['properties']['building_type'] and f['properties']['building_type'] != '-')
print(f'\nWith tax: {with_tax}/{len(d["features"])}')
print(f'With type: {with_type}/{len(d["features"])}')
