import sys
from ontogpt.webapp.ontology_inspector import parse_owl_to_explorer_model
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

owl_xml = Path("C:/Users/cj/Downloads/extraction_result_optimized.owl").read_text(encoding="utf-8")
data = parse_owl_to_explorer_model(owl_xml, max_graph_nodes=100, search_keyword="励磁系统")
print("Total individuals matched in inspector:", len(data['individuals']))
for ind in data['individuals']:
    print(f" - {ind['label']} ({ind['types'][0].split('/')[-1] if ind['types'] else 'none'})")
