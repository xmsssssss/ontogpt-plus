import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

s_root = rdflib.URIRef("http://example.org/NOPREFIX/20231027_01")
print("Types of s_root:", list(g.objects(s_root, rdflib.RDF.type)))
