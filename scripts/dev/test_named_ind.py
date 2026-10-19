import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

named_inds = set(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual))
print("Total OWL:NamedIndividuals in g:", len(named_inds))

s_root = rdflib.URIRef("http://example.org/NOPREFIX/20231027_01")
print("Is s_root in named_inds?", s_root in named_inds)
