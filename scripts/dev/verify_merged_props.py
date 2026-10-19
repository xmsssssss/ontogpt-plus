import sys, rdflib
from ontogpt.webapp.main import task_storage
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

tasks = task_storage.list_tasks(limit=500)
merged_graph = rdflib.Graph()
for t in tasks:
    if t.get('status') == 'completed' and t.get('has_result'):
        detail = task_storage.get_task(t['id'])
        if detail and detail.get('result'):
            owl_data = detail['result'].get('owl_output', '')
            if owl_data and '<rdf:RDF' in owl_data:
                try:
                    merged_graph.parse(data=owl_data, format='xml')
                except Exception:
                    pass

target_uri = rdflib.URIRef("https://w3id.org/ontogpt/auto_schema_309c131b/ind/AuxiliarySystem_%E6%B6%A6%E6%BB%91%E6%B2%B9%E7%B3%BB%E7%BB%9F_65079b08")
print("=== Consolidated Properties for 'AuxiliarySystem_润滑油系统' ===")
props = {}
for p, o in merged_graph.predicate_objects(target_uri):
    p_name = str(p).split('/')[-1]
    if p_name not in props:
        props[p_name] = set()
    props[p_name].add(unquote(str(o)))

for k, vals in props.items():
    print(f"  {k} ({len(vals)} merged values):")
    for v in list(vals)[:4]:
        print(f"     - {v}")
    if len(vals) > 4:
        print(f"     ... and {len(vals)-4} more")
