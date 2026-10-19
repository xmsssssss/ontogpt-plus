import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.webapp.main import task_storage

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_data = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=owl_data, format='xml')

print("=== Checking object-like literal properties ===")
sample_props = set()
for s, p, o in g:
    p_name = str(p).split('/')[-1]
    if any(k in p_name.lower() for k in ['system', 'component', 'equipment', 'target', 'source', 'context', 'unit']):
        sample_props.add(p_name)

print("Properties with entity link semantics:", sample_props)

for p_name in ['unit_or_context', 'material_target', 'component_name', 'key_components', 'cooling_source']:
    examples = []
    for s, p, o in g:
        if str(p).split('/')[-1] == p_name and isinstance(o, rdflib.Literal):
            examples.append((unquote(str(s).split('/')[-1]), unquote(str(o))))
    print(f"\nSample values for {p_name} (total {len(examples)}):")
    for s_val, o_val in examples[:5]:
        print(f"   {s_val}  --[{p_name}]-->  {o_val}")
