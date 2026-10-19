import sys, rdflib
from ontogpt.webapp.ontology_inspector import parse_owl_to_explorer_model
from ontogpt.webapp.main import task_storage
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

owl_xml = merged_graph.serialize(format='pretty-xml', encoding='utf-8').decode('utf-8')
model = parse_owl_to_explorer_model(owl_xml, max_graph_nodes=5000)

graph = model.get('graph', {})
links = graph.get('links', [])
print(f"Total nodes in model graph: {len(graph.get('nodes', []))}")
print(f"Total links in model graph: {len(links)}")
if links:
    print("Sample link:", links[0])
