import urllib.request, json, sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:8000/api/ontology/search?query=%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F'
res = urllib.request.urlopen(url)
data = json.loads(res.read().decode('utf-8'))

print("=== API returned results for '励磁系统': ===")
for i, r in enumerate(data['results'][:10], 1):
    print(f"[{i}] {r['entity']['label']} | class: {r['entity']['class_type']}")
    print(f"    IRI: {r['entity']['iri']}")
    print(f"    Attributes: {r['attributes']}")
    print(f"    Relationships: {r['relationships']}")
    print()
