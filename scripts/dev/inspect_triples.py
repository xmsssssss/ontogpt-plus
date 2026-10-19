import sys, rdflib
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.webapp.main import task_storage

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_data = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=owl_data, format='xml')

print("Total triples in Graph:", len(g))

# 统计所有谓词 (Predicates)
pred_counts = {}
for p in g.predicates():
    p_str = str(p)
    pred_counts[p_str] = pred_counts.get(p_str, 0) + 1

print("\nPredicates distribution:")
for p, count in sorted(pred_counts.items(), key=lambda x: x[1], reverse=True)[:25]:
    print(f" - {p}: {count}")

# 统计个体到个体的对象属性 (Object Properties between Individuals)
obj_triples = []
for s, p, o in g:
    if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
        if p not in [rdflib.RDF.type, rdflib.RDFS.subClassOf, rdflib.OWL.sameAs]:
            obj_triples.append((s, p, o))

print(f"\nTotal individual-to-individual/class object triples: {len(obj_triples)}")
for s, p, o in obj_triples[:10]:
    print("  s:", str(s).split('/')[-1])
    print("  p:", str(p).split('/')[-1])
    print("  o:", str(o).split('/')[-1])
    print()
