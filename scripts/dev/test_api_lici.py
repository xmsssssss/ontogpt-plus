import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

res = urllib.request.urlopen('http://127.0.0.1:8000/api/ontology/search?query=%E5%8A%B1%E7%A3%81')
data = json.loads(res.read().decode('utf-8'))
print(f"Total matched for '励磁': {data['matched_count']}")
for i, r in enumerate(data['results'][:8], 1):
    print(f"[{i}] {r['entity']['label']} ({r['entity']['class_type']})")
    for k, v in r['attributes'].items():
        print(f"     {k}: {v}")
