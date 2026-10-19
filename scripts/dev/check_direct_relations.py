import sys, rdflib
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.webapp.main import task_storage

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_data = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=owl_data, format='xml')

direct_relations = []
for s, p, o in g:
    if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
        s_name = str(s).split('/')[-1]
        o_name = str(o).split('/')[-1]
        p_name = str(p).split('/')[-1]
        # 排除 20231027_01 (Report container) 以及 rdf:type / subClassOf
        if not s_name.startswith("20231027") and not o_name.startswith("20231027"):
            if p not in [rdflib.RDF.type, rdflib.RDFS.subClassOf, rdflib.OWL.sameAs]:
                direct_relations.append((s_name, p_name, o_name))

print("Direct individual-to-individual relations (excluding container):", len(direct_relations))
for r in direct_relations[:10]:
    print(r)
