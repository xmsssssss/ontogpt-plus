import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

s_root = rdflib.URIRef("http://example.org/NOPREFIX/20231027_01")
for p, o in g.predicate_objects(s_root):
    o_str = unquote(str(o))
    if "励磁" in o_str:
        print(f"Root link: {str(p).split('/')[-1]} -> {o_str.split('/')[-1]}")
