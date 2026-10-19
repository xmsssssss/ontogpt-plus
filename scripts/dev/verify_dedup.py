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

print("=== Checking entities after deduplication ===")
lub_inds = set()
for s in set(merged_graph.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual)):
    s_clean = unquote(str(s))
    if "AuxiliarySystem" in s_clean and "润滑油系统" in s_clean:
        lub_inds.add(s_clean)

print(f"Total AuxiliarySystem '润滑油系统' instances in database: {len(lub_inds)}")
for ind in sorted(lub_inds):
    print(" -", ind.split('/')[-1])
