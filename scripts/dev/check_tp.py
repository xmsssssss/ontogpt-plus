import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

s_target = rdflib.URIRef("https://w3id.org/ontogpt/auto_schema_309c131b/ind/TechnicalProcess_%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F%E6%81%92%E7%94%B5%E5%8E%8B_%E6%81%92%E7%94%B5%E6%B5%81_%E6%81%92%E6%97%A0%E5%8A%9F_%E6%81%92%E5%8A%9F%E7%8E%87%E5%9B%A0%E6%95%B0%E8%B0%83%E8%8A%82_d98828f9")
print("Target in g subjects?", s_target in set(g.subjects()))
print("Types of target:", list(g.objects(s_target, rdflib.RDF.type)))
