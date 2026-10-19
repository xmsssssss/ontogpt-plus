import sys, rdflib
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.webapp.ontology_inspector import parse_owl_to_explorer_model
from ontogpt.webapp.main import task_storage
from ontogpt.clients.neo4j_service import neo4j_service

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_data = detail['result'].get('owl_output', '')
model = parse_owl_to_explorer_model(owl_data, max_graph_nodes=2000)
nodes = model.get('graph', {}).get('nodes', [])
links = model.get('graph', {}).get('links', [])

print(f"Total graph nodes: {len(nodes)}")
print(f"Total graph links: {len(links)}")

node_iris = {n['id'] for n in nodes}
link_types = set()
for l in links:
    link_types.add(l.get('label'))

print(f"Link types found in model: {link_types}")

with neo4j_service.get_driver().session(database='ont') as session:
    res = session.run("MATCH (n:Entity) RETURN count(n) AS c").single()['c']
    print(f"Current entities in Neo4j: {res}")
