import sys, rdflib
from ontogpt.webapp.main import task_storage
from ontogpt.webapp.ontology_inspector import parse_owl_to_explorer_model
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

merged_xml = merged_graph.serialize(format='pretty-xml', encoding='utf-8').decode('utf-8')
data = parse_owl_to_explorer_model(merged_xml, max_graph_nodes=100, search_keyword="励磁系统")
print("Matched in merged_graph:", len(data['individuals']))
for ind in data['individuals']:
    print(f" - {ind['label']} ({ind['types'][0].split('/')[-1] if ind['types'] else 'none'})")
