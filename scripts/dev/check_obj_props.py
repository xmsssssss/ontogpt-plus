import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

obj_props = set(g.subjects(rdflib.RDF.type, rdflib.OWL.ObjectProperty))
print(f"Total Object Properties in schema: {len(obj_props)}")
for op in obj_props:
    print(" -", str(op).split('/')[-1])

print("\nSample Object Property triples (excluding root 20231027_01):")
count = 0
for s, p, o in g:
    if p in obj_props and "20231027_01" not in str(s):
        print(f"  {unquote(str(s)).split('/')[-1]} --[{str(p).split('/')[-1]}]--> {unquote(str(o)).split('/')[-1]}")
        count += 1
        if count >= 10:
            break
if count == 0:
    print("  None found between leaf individuals!")
