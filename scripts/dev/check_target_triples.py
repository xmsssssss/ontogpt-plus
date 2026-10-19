import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

target_uri = rdflib.URIRef("https://w3id.org/ontogpt/auto_schema_309c131b/ind/EquipmentComponent_%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F_da4ff88c")

print("=== Direct triples for EquipmentComponent_励磁系统 ===")
for p, o in g.predicate_objects(target_uri):
    print(f"  Outgoing: {str(p).split('/')[-1]} -> {unquote(str(o))}")

print("\n=== Incoming triples to EquipmentComponent_励磁系统 ===")
for s, p in g.subject_predicates(target_uri):
    s_clean = unquote(str(s)).split('/')[-1]
    p_clean = str(p).split('/')[-1]
    print(f"  Incoming: {s_clean} -[{p_clean}]-> 励磁系统")
