import re, hashlib
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import unquote
import rdflib

def extract_rdf_graph_for_neo4j(owl_xml: str):
    g = rdflib.Graph()
    g.parse(data=owl_xml, format="xml")

    # 1. 抽取所有的 Class 节点
    classes_dict = {}
    for c in g.subjects(rdflib.RDF.type, rdflib.OWL.Class):
        c_uri = str(c)
        c_label = str(g.value(c, rdflib.RDFS.label) or c_uri.split('/')[-1].split('#')[-1])
        classes_dict[c_uri] = {
            "iri": c_uri,
            "name": c_label,
            "label": c_label,
            "type": "Class",
            "attrs": {"is_owl_class": True}
        }

    # 2. 抽取所有的 NamedIndividual 实体节点及属性
    ind_nodes_dict = {}
    for ind in g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual):
        ind_uri = str(ind)
        # 获取类型
        types = [str(t).split('/')[-1].split('#')[-1] for t in g.objects(ind, rdflib.RDF.type) if t != rdflib.OWL.NamedIndividual]
        primary_type = types[0] if types else "Entity"

        # 获取展示名与属性
        raw_local = unquote(ind_uri.split('/')[-1])
        parts = raw_local.split('_')
        if len(parts) >= 3 and len(parts[-1]) in [6, 8, 10]:
            name = "_".join(parts[1:-1])
        else:
            name = raw_local

        label = str(g.value(ind, rdflib.RDFS.label) or name)

        attrs = {}
        for p, o in g.predicate_objects(ind):
            if isinstance(o, rdflib.Literal):
                p_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(p).split('/')[-1].split('#')[-1])
                lit_val = str(o).strip()
                if p_name not in attrs:
                    attrs[p_name] = lit_val

        ind_nodes_dict[ind_uri] = {
            "iri": ind_uri,
            "name": name,
            "label": label,
            "type": primary_type,
            "attrs": attrs
        }

    # 3. 抽取全部对象关系连边
    edges = []
    # (a) 个体 -> 类 (IS_A_TYPE)
    for ind_uri, item in ind_nodes_dict.items():
        ind_ref = rdflib.URIRef(ind_uri)
        for t in g.objects(ind_ref, rdflib.RDF.type):
            t_uri = str(t)
            if t_uri in classes_dict:
                edges.append({"source": ind_uri, "target": t_uri, "type": "IS_A_TYPE"})

    # (b) 类 -> 父类 (SUBCLASS_OF)
    for c_uri in classes_dict:
        c_ref = rdflib.URIRef(c_uri)
        for parent in g.objects(c_ref, rdflib.RDFS.subClassOf):
            p_uri = str(parent)
            if p_uri in classes_dict:
                edges.append({"source": c_uri, "target": p_uri, "type": "SUBCLASS_OF"})

    # (c) 个体与个体之间的对象属性连边 (OBJECT PROPERTIES)
    for s, p, o in g:
        if isinstance(s, rdflib.URIRef) and isinstance(o, rdflib.URIRef):
            if p not in [rdflib.RDF.type, rdflib.RDFS.subClassOf, rdflib.OWL.sameAs]:
                s_uri = str(s)
                o_uri = str(o)
                # 确保主体或客体至少一个是库内有效节点
                if s_uri in ind_nodes_dict or o_uri in ind_nodes_dict:
                    rel_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(p).split('/')[-1].split('#')[-1]).upper()
                    edges.append({"source": s_uri, "target": o_uri, "type": rel_name})

    # (d) 基于属性中引用的具名部件建立跨实体拓扑关联 (Domain Component Linking)
    name_to_iri = {}
    for ind_uri, item in ind_nodes_dict.items():
        n = item["name"]
        if len(n) >= 2 and n not in ["None", "null", "未命名"]:
            name_to_iri[n] = ind_uri

    for ind_uri, item in ind_nodes_dict.items():
        attrs = item["attrs"]
        for ref_field in ["key_components", "component_name", "material_target", "subsystem_of", "source"]:
            if ref_field in attrs:
                target_name = attrs[ref_field]
                if target_name in name_to_iri and name_to_iri[target_name] != ind_uri:
                    edges.append({
                        "source": ind_uri,
                        "target": name_to_iri[target_name],
                        "type": ref_field.upper()
                    })

    # 补充未注册为独立节点的 Subject（如 20231027_01 报告容器）
    extra_nodes = {}
    for e in edges:
        s_u = e["source"]
        t_u = e["target"]
        if s_u not in ind_nodes_dict and s_u not in classes_dict and s_u not in extra_nodes:
            s_name = s_u.split('/')[-1]
            extra_nodes[s_u] = {"iri": s_u, "name": s_name, "label": s_name, "type": "ReportContainer", "attrs": {}}
        if t_u not in ind_nodes_dict and t_u not in classes_dict and t_u not in extra_nodes:
            t_name = t_u.split('/')[-1]
            extra_nodes[t_u] = {"iri": t_u, "name": t_name, "label": t_name, "type": "Entity", "attrs": {}}

    all_nodes = list(classes_dict.values()) + list(ind_nodes_dict.values()) + list(extra_nodes.values())
    return all_nodes, edges

from ontogpt.webapp.main import task_storage
detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
nodes, links = extract_rdf_graph_for_neo4j(detail['result']['owl_output'])
print(f"Total Nodes prepared: {len(nodes)}")
print(f"Total Links prepared: {len(links)}")
print("Sample link 1:", links[0])
print("Sample link 100:", links[100])
print("Sample link last:", links[-1])
