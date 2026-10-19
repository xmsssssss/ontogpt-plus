"""Ontology Graph & Model Inspector for Ontology Explorer Web UI."""

import logging
import re
from typing import Any, Dict, List, Optional, Set
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef, Literal, BNode

logger = logging.getLogger(__name__)


def parse_owl_to_explorer_model(
    owl_xml_content: str,
    max_graph_nodes: int = 150,
    search_keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse an OWL 2 RDF/XML string into an interactive ontology model containing:
    1. Metadata (Ontology IRI, version, label, description)
    2. Hierarchy trees (Classes, Object Properties, Data Properties)
    3. Individuals list with types and property assertions
    4. Force-directed graph payload (nodes and links) for knowledge graph visualization
    Supports semantic sub-graph filtering by `search_keyword`.
    """
    g = rdflib.Graph()
    try:
        g.parse(data=owl_xml_content, format="xml")
    except Exception as e:
        logger.warning(f"Failed to parse OWL XML in explorer parser: {e}")
        return {
            "success": False,
            "error": str(e),
            "classes": [],
            "object_properties": [],
            "data_properties": [],
            "individuals": [],
            "graph": {"nodes": [], "links": []},
            "stats": {"classes_count": 0, "individuals_count": 0, "triples_count": 0},
        }

    # 1. Ontology metadata
    ont_uris = list(g.subjects(RDF.type, OWL.Ontology))
    ont_uri = str(ont_uris[0]) if ont_uris else ""
    ont_label = str(g.value(ont_uris[0], RDFS.label) or ont_uri) if ont_uris else "Ontology"
    ont_comment = str(g.value(ont_uris[0], RDFS.comment) or "") if ont_uris else ""

    # 2. Classes and class hierarchy
    classes_dict: Dict[str, Dict[str, Any]] = {}
    class_uris = set(g.subjects(RDF.type, OWL.Class))
    for s, p, o in g:
        if p == RDF.type and isinstance(o, URIRef) and o not in [OWL.NamedIndividual, OWL.Class]:
            class_uris.add(o)

    for c in class_uris:
        c_str = str(c)
        local_name = c_str.split("/")[-1].split("#")[-1]
        label = str(g.value(c, RDFS.label) or local_name)
        comment = str(g.value(c, RDFS.comment) or "")
        parents = [str(parent) for parent in g.objects(c, RDFS.subClassOf) if isinstance(parent, URIRef)]
        classes_dict[c_str] = {
            "uri": c_str,
            "name": local_name,
            "label": label,
            "comment": comment,
            "parents": parents,
            "instances_count": 0,
        }

    # 3. Object Properties & Characteristics
    obj_props_dict: Dict[str, Dict[str, Any]] = {}
    obj_prop_uris = set(g.subjects(RDF.type, OWL.ObjectProperty))
    for p in obj_prop_uris:
        p_str = str(p)
        local_name = p_str.split("/")[-1].split("#")[-1]
        label = str(g.value(p, RDFS.label) or local_name)
        comment = str(g.value(p, RDFS.comment) or "")
        domain = [str(d) for d in g.objects(p, RDFS.domain)]
        rng = [str(r) for r in g.objects(p, RDFS.range)]
        chars = []
        if (p, RDF.type, OWL.TransitiveProperty) in g:
            chars.append("Transitive")
        if (p, RDF.type, OWL.SymmetricProperty) in g:
            chars.append("Symmetric")
        if (p, RDF.type, OWL.AsymmetricProperty) in g:
            chars.append("Asymmetric")
        if (p, RDF.type, OWL.ReflexiveProperty) in g:
            chars.append("Reflexive")
        if (p, RDF.type, OWL.IrreflexiveProperty) in g:
            chars.append("Irreflexive")
        if (p, RDF.type, OWL.FunctionalProperty) in g:
            chars.append("Functional")

        obj_props_dict[p_str] = {
            "uri": p_str,
            "name": local_name,
            "label": label,
            "comment": comment,
            "domain": domain,
            "range": rng,
            "characteristics": chars,
        }

    # 4. Data Properties
    data_props_dict: Dict[str, Dict[str, Any]] = {}
    data_prop_uris = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    for p in data_prop_uris:
        p_str = str(p)
        local_name = p_str.split("/")[-1].split("#")[-1]
        label = str(g.value(p, RDFS.label) or local_name)
        comment = str(g.value(p, RDFS.comment) or "")
        chars = []
        if (p, RDF.type, OWL.FunctionalProperty) in g:
            chars.append("Functional")

        data_props_dict[p_str] = {
            "uri": p_str,
            "name": local_name,
            "label": label,
            "comment": comment,
            "characteristics": chars,
        }

    # 5. Individuals and property assertions
    ind_dict: Dict[str, Dict[str, Any]] = {}
    from urllib.parse import unquote

    for s, p, o in g:
        if p == RDF.type and o in [OWL.NamedIndividual]:
            s_str = str(s)
            if s_str not in ind_dict:
                raw_local = s_str.split("/")[-1].split("#")[-1]
                decoded_local = unquote(raw_local)

                # 获取规范业务名称（去除 ClassPrefix_ 和末尾的 _hash8）
                display_name = decoded_local
                parts = decoded_local.split("_")
                if len(parts) >= 3 and len(parts[-1]) in [6, 8, 10]:
                    display_name = "_".join(parts[1:-1])
                elif len(parts) == 2 and len(parts[-1]) in [6, 8, 10]:
                    display_name = parts[0]

                raw_label = g.value(s, RDFS.label)
                if raw_label:
                    label_str = unquote(str(raw_label).strip())
                    # 如果原 label 是机器生成的 URI 格式（如 Class_Name_hash），同样清洗
                    if "_" in label_str:
                        l_parts = label_str.split("_")
                        if len(l_parts) >= 3 and len(l_parts[-1]) in [6, 8, 10]:
                            final_label = "_".join(l_parts[1:-1])
                        else:
                            final_label = label_str
                    else:
                        final_label = label_str
                else:
                    final_label = display_name

                ind_dict[s_str] = {
                    "uri": s_str,
                    "name": final_label,
                    "label": final_label,
                    "types": [],
                    "data_properties": {},
                    "object_properties": {},
                }

    for ind_uri, ind_data in ind_dict.items():
        subj = URIRef(ind_uri)
        # Types
        for t in g.objects(subj, RDF.type):
            if t != OWL.NamedIndividual and isinstance(t, URIRef):
                t_str = str(t)
                ind_data["types"].append(t_str)
                if t_str in classes_dict:
                    classes_dict[t_str]["instances_count"] += 1

        # Properties
        for p, o in g.predicate_objects(subj):
            if p in [RDF.type, RDFS.label]:
                continue
            p_str = str(p)
            p_local = p_str.split("/")[-1].split("#")[-1]
            if isinstance(o, URIRef) and str(o) in ind_dict:
                # Object property pointing to another individual
                if p_local not in ind_data["object_properties"]:
                    ind_data["object_properties"][p_local] = []
                ind_data["object_properties"][p_local].append({
                    "uri": str(o),
                    "name": ind_dict[str(o)]["name"],
                    "label": ind_dict[str(o)]["label"],
                })
            elif isinstance(o, Literal):
                # Data property
                if p_local not in ind_data["data_properties"]:
                    ind_data["data_properties"][p_local] = []
                ind_data["data_properties"][p_local].append(str(o))

    # 6. Graph visualization payload (Nodes and Links)
    graph_nodes = []
    graph_links = []
    node_set = set()

    clean_kw = (search_keyword or "").strip().lower()

    all_inds = list(ind_dict.values())
    if clean_kw:
        # 关键词聚焦模式：筛选名字、标签或属性中包含关键词的实体
        matched_inds = []
        for ind in all_inds:
            searchable_text = f"{ind['label']} {ind['name']} {' '.join(ind['types'])} "
            for vals in ind['data_properties'].values():
                searchable_text += " ".join(vals) + " "
            for rel_name, rel_targets in ind['object_properties'].items():
                searchable_text += f"{rel_name} " + " ".join(t.get('label', '') for t in rel_targets) + " "
            if clean_kw in searchable_text.lower():
                matched_inds.append(ind)
        selected_inds = matched_inds[:max_graph_nodes]
        returned_individuals = matched_inds
    else:
        selected_inds = all_inds[:max_graph_nodes]
        returned_individuals = all_inds

    selected_uris = {ind["uri"] for ind in selected_inds}

    # 确定关联的 Class 节点
    relevant_class_uris = set()
    for ind in selected_inds:
        for t_uri in ind["types"]:
            relevant_class_uris.add(t_uri)

    if not clean_kw:
        for c_uri in list(classes_dict.keys())[:20]:
            relevant_class_uris.add(c_uri)

    # Add Class nodes
    for c_uri in relevant_class_uris:
        if c_uri in classes_dict:
            c = classes_dict[c_uri]
            graph_nodes.append({
                "id": c["uri"],
                "name": c["label"] or c["name"],
                "group": "Class",
                "type": "owl:Class",
                "val": 18,
                "color": "#4f46e5",  # Indigo
            })
            node_set.add(c["uri"])
            for parent_uri in c["parents"]:
                if parent_uri in relevant_class_uris:
                    graph_links.append({
                        "source": c["uri"],
                        "target": parent_uri,
                        "label": "subClassOf",
                        "color": "#94a3b8",
                    })

    # Add Individual nodes
    for ind in selected_inds:
        graph_nodes.append({
            "id": ind["uri"],
            "name": ind["label"] or ind["name"],
            "group": "Individual",
            "type": ind["types"][0].split("/")[-1] if ind["types"] else "NamedIndividual",
            "val": 12,
            "color": "#0ea5e9",  # Cyan/Blue
        })
        node_set.add(ind["uri"])

        # Link individual to its Class
        for t_uri in ind["types"]:
            if t_uri in node_set:
                graph_links.append({
                    "source": ind["uri"],
                    "target": t_uri,
                    "label": "rdf:type",
                    "color": "#cbd5e1",
                })

        # Object property links between individuals
        for prop_name, targets in ind["object_properties"].items():
            for target in targets:
                if target["uri"] in selected_uris:
                    graph_links.append({
                        "source": ind["uri"],
                        "target": target["uri"],
                        "label": prop_name,
                        "color": "#f59e0b",  # Amber
                    })

    return {
        "success": True,
        "metadata": {
            "uri": ont_uri,
            "label": ont_label,
            "comment": ont_comment,
        },
        "stats": {
            "classes_count": len(classes_dict),
            "object_properties_count": len(obj_props_dict),
            "data_properties_count": len(data_props_dict),
            "individuals_count": len(ind_dict),
            "triples_count": len(g),
        },
        "classes": list(classes_dict.values()),
        "object_properties": list(obj_props_dict.values()),
        "data_properties": list(data_props_dict.values()),
        "individuals": returned_individuals[:300],  # Return up to 300 for tabular explorer
        "graph": {
            "nodes": graph_nodes,
            "links": graph_links,
        },
    }
