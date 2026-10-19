import sys, urllib.request, json
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:8000/api/ontology/search?query=%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F'
res = urllib.request.urlopen(url)
data = json.loads(res.read().decode('utf-8'))

for i, r in enumerate(data['results'], 1):
    label = r['entity']['label']
    c_type = r['entity']['class_type']
    if c_type == 'AutoSchema309c131bReport':
        print(f"[{i}] Root Report (contains {len(r['relationships'])} links)")
    else:
        print(f"[{i}] {label} ({c_type})")
        for k, v in r['attributes'].items():
            print(f"     {k}: {v}")
