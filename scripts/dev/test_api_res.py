import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

res = urllib.request.urlopen('http://127.0.0.1:8000/api/ontology/search?query=%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F')
data = json.loads(res.read().decode('utf-8'))
for i, r in enumerate(data['results']):
    print(f"[{i}] {r['entity']['label']} ({r['entity']['class_type']})")
    print("    attrs:", r['attributes'])
    print("    rels:", [(x['predicate'], x['target_name']) for x in r['relationships'][:5]])
