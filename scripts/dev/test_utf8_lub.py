import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

res = urllib.request.urlopen('http://127.0.0.1:8000/api/ontology/search?query=%E6%B6%A6%E6%BB%91%E6%B2%B9%E7%B3%BB%E7%BB%9F')
data = json.loads(res.read().decode('utf-8'))
for i, r in enumerate(data['results'][:6], 1):
    ent = r['entity']
    attrs = r['attributes']
    print(f"[{i}] {ent['label']} ({ent['class_type']})")
    for k, v in attrs.items():
        print(f"     {k}: {v}")
