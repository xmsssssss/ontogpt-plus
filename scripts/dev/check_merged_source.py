import sys, rdflib
from ontogpt.webapp.main import task_storage
sys.stdout.reconfigure(encoding='utf-8')

tasks = task_storage.list_tasks(limit=500)
completed_with_result = [t for t in tasks if t.get('status') == 'completed' and t.get('has_result')]
print(f"Total completed tasks with result: {len(completed_with_result)}")

merged_graph = rdflib.Graph()
for t in completed_with_result:
    detail = task_storage.get_task(t['id'])
    if detail and detail.get('result'):
        owl_data = detail['result'].get('owl_output', '')
        if owl_data and '<rdf:RDF' in owl_data:
            try:
                merged_graph.parse(data=owl_data, format='xml')
            except Exception as e:
                print("Error parsing task:", t['id'], e)

print(f"Total triples in merged_graph from task_storage: {len(merged_graph)}")
