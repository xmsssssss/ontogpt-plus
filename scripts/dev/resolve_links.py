import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')
from ontogpt.webapp.main import task_storage

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
owl_data = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=owl_data, format='xml')

# 收集所有已知的具名实体及其中文名称
entities = {}
for s in g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual):
    s_uri = str(s)
    raw_local = unquote(s_uri.split('/')[-1])
    # 提取中文名称
    parts = raw_local.split('_')
    if len(parts) >= 3:
        c_name = parts[0]
        ent_name = "_".join(parts[1:-1])
        if len(ent_name) >= 2: # 忽略单字或空名
            entities[ent_name] = (s_uri, c_name)

print(f"Total recognizable named entities: {len(entities)}")

# 1. key_components 关联 (AuxiliarySystem -> EquipmentComponent)
key_comp_links = []
for s, p, o in g:
    p_name = str(p).split('/')[-1]
    if p_name == 'key_components' and isinstance(o, rdflib.Literal):
        comp_val = unquote(str(o)).strip()
        # 模糊匹配或精准匹配已知实体
        for ent_name, (target_uri, target_cls) in entities.items():
            if ent_name == comp_val or (len(comp_val) >= 3 and comp_val in ent_name):
                key_comp_links.append((str(s), "HAS_KEY_COMPONENT", target_uri, comp_val, ent_name))
                break

print(f"Resolved HAS_KEY_COMPONENT links: {len(key_comp_links)}")
for s, rel, t, c_v, e_n in key_comp_links[:5]:
    print(f"   {unquote(s.split('/')[-1])} --[{rel}]--> {unquote(t.split('/')[-1])} (via '{c_v}')")

# 2. 属于同一个文档章节/Chunk (Co-occurrence in chunks)
# 检查 Report 挂载的各个集合
container_links = []
for s, p, o in g:
    if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
        p_name = str(p).split('/')[-1]
        if p_name in ['equipment_components', 'technical_processes', 'performance_parameters', 'auxiliary_systems', 'operational_modes']:
            container_links.append((str(s), p_name, str(o)))

print(f"Report container aggregation links: {len(container_links)}")
