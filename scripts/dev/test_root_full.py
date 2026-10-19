import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

s_root = rdflib.URIRef("http://example.org/NOPREFIX/20231027_01")
for s, p, o in g.triples((None, None, s_root)):
    print("Subject pointing to s_root:", s, p)
for s, p, o in g.triples((s_root, None, None)):
    if p == rdflib.RDF.type:
        print("Root type:", o)
