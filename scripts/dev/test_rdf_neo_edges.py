import sys, rdflib
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.clients.neo4j_service import neo4j_service
from ontogpt.webapp.main import task_storage

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_xml = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=owl_xml, format='xml')

print("=== Direct RDF Graph-level extraction for Neo4j Sync ===")
# 1. 收集 Class
classes = set(g.subjects(rdflib.RDF.type, rdflib.OWL.Class))
# 2. 收集 NamedIndividual
individuals = set(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual))
# 3. 收集所有个体/类之间的关系连边
edges = []
for s, p, o in g:
    if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
        p_str = str(p)
        if p == rdflib.RDF.type and o in classes:
            edges.append((str(s), "IS_A_TYPE", str(o)))
        elif p == rdflib.RDFS.subClassOf and o in classes:
            edges.append((str(s), "SUBCLASS_OF", str(o)))
        elif p not in [rdflib.RDF.type, rdflib.RDFS.subClassOf, rdflib.OWL.sameAs]:
            edges.append((str(s), str(p).split('/')[-1].split('#')[-1].upper(), str(o)))

print(f"Total Classes: {len(classes)}")
print(f"Total Individuals: {len(individuals)}")
print(f"Total RDF Object Edges: {len(edges)}")
print("Sample edges:")
for e in edges[:10]:
    print(" ", e)
