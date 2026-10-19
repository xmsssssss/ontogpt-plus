import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

s_target = rdflib.URIRef("https://w3id.org/ontogpt/auto_schema_309c131b/ind/EquipmentComponent_%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F_485450fe")
print("=== Incoming to EquipmentComponent_励磁系统_485450fe ===")
for s, p in g.subject_predicates(s_target):
    s_clean = unquote(str(s)).split('/')[-1]
    p_clean = str(p).split('/')[-1]
    print(f"  Incoming: {s_clean} -[{p_clean}]-> 励磁系统")
