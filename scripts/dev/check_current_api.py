import urllib.request, json
res = urllib.request.urlopen('http://127.0.0.1:8000/api/ontology/search?query=%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F')
data = json.loads(res.read().decode('utf-8'))
print("Current API returned count:", data['matched_count'])
for r in data['results']:
    print(r['entity']['label'], r['entity']['class_type'])
