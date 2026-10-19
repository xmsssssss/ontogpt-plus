"""
Neo4j Knowledge Graph Service & Bidirectional Extraction Integrator.

Provides:
1. Connection management & health checks for Neo4j.
2. Ingestion: Idempotent sync of OWL 2 knowledge ontologies into Neo4j Labeled Property Graphs.
3. Pre-extraction Lookup: Fast graph query during SPIRES extraction to reuse known entity profiles.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

from neo4j import GraphDatabase, Driver
import rdflib

logger = logging.getLogger(__name__)

DEFAULT_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
DEFAULT_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
DEFAULT_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
DEFAULT_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


class Neo4jKnowledgeService:
    def __init__(
        self,
        uri: str = DEFAULT_NEO4J_URI,
        user: str = DEFAULT_NEO4J_USER,
        password: str = DEFAULT_NEO4J_PASSWORD,
        database: str = DEFAULT_NEO4J_DATABASE,
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: Optional[Driver] = None

    def get_driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                connection_timeout=3.0,
                max_connection_lifetime=60,
            )
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def test_connection(self) -> Dict[str, Any]:
        """Test connectivity and return server version and node count."""
        try:
            driver = self.get_driver()
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS alive")
                record = result.single()
                if record and record["alive"] == 1:
                    count_rec = session.run("MATCH (n) RETURN count(n) AS total_nodes").single()
                    total_nodes = count_rec["total_nodes"] if count_rec else 0
                    return {
                        "connected": True,
                        "uri": self.uri,
                        "database": self.database,
                        "total_nodes": total_nodes,
                    }
        except Exception as e:
            logger.warning(f"Neo4j connection test failed: {e}")
            return {"connected": False, "uri": self.uri, "database": self.database, "error": str(e)}
        return {"connected": False, "uri": self.uri, "database": self.database, "error": "Unknown error"}

    def lookup_entity(self, name: str, class_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        在抽取阶段预查 Neo4j：
        如果已存在该实体且包含完备属性，直接返回供 SPIRES 引擎复用，免去大模型重复调用。
        """
        clean_name = name.strip()
        if not clean_name:
            return None

        driver = self.get_driver()
        try:
            with driver.session(database=self.database) as session:
                query = """
                MATCH (n)
                WHERE (n.name = $name OR n.label = $name)
                """
                if class_type:
                    query += f" AND '{class_type}' IN labels(n)"
                query += " RETURN n, labels(n) AS labels LIMIT 1"

                result = session.run(query, name=clean_name)
                record = result.single()
                if not record:
                    return None

                node = record["n"]
                props = dict(node)

                # 格式化为 SPIRES 期待的响应字典结构
                output_dict: Dict[str, Any] = {}
                for k, v in props.items():
                    if k in ["iri", "updated_at", "created_at"]:
                        continue
                    output_dict[k] = v

                return output_dict
        except Exception as e:
            logger.debug(f"Neo4j entity lookup failed: {e}")
            return None

    def sync_owl_to_neo4j(self, owl_xml_content: str) -> Dict[str, Any]:
        """
        将 OWL 2 RDF/XML 数据全量/增量同步到 Neo4j：
        1. 抽取所有的 Class、Individual 及 Report 节点；
        2. 节点与类标签 MERGE（按 IRI 唯一性幂等更新）；
        3. 关系连边 MERGE（包括实体类型归属、父类层级、对象属性及部件跨实体关联）。
        """
        if not owl_xml_content or "<rdf:RDF" not in owl_xml_content:
            return {"success": False, "message": "No valid RDF/XML content found."}

        g = rdflib.Graph()
        try:
            g.parse(data=owl_xml_content, format="xml")
        except Exception as e:
            return {"success": False, "error": f"Failed to parse RDF/XML: {e}"}

        # 1. 抽取所有的 Class 节点
        classes_dict: Dict[str, Dict[str, Any]] = {}
        for c in g.subjects(rdflib.RDF.type, rdflib.OWL.Class):
            c_uri = str(c)
            c_label = str(g.value(c, rdflib.RDFS.label) or c_uri.split('/')[-1].split('#')[-1])
            classes_dict[c_uri] = {
                "iri": c_uri,
                "name": c_label,
                "label": c_label,
                "primary_type": "Class",
                "attrs": {"is_owl_class": True},
            }

        # 2. 抽取所有的 NamedIndividual 实体节点及属性
        ind_nodes_dict: Dict[str, Dict[str, Any]] = {}
        for ind in g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual):
            ind_uri = str(ind)
            types = [
                str(t).split('/')[-1].split('#')[-1]
                for t in g.objects(ind, rdflib.RDF.type)
                if t != rdflib.OWL.NamedIndividual
            ]
            primary_type = types[0] if types else "Entity"
            safe_type = re.sub(r"[^a-zA-Z0-9_]", "_", primary_type)

            raw_local = unquote(ind_uri.split('/')[-1])
            parts = raw_local.split('_')
            if len(parts) >= 3 and len(parts[-1]) in [6, 8, 10]:
                name = "_".join(parts[1:-1])
            else:
                name = raw_local

            label = str(g.value(ind, rdflib.RDFS.label) or name)

            attrs: Dict[str, Any] = {}
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
                "primary_type": safe_type,
                "attrs": attrs,
            }

        # 3. 抽取全部对象关系连边
        edges: List[Dict[str, str]] = []
        # (a) 个体 -> 类 (IS_A_TYPE)
        for ind_uri in ind_nodes_dict:
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
                    if s_uri in ind_nodes_dict or o_uri in ind_nodes_dict:
                        rel_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(p).split('/')[-1].split('#')[-1]).upper()
                        edges.append({"source": s_uri, "target": o_uri, "type": rel_name})

        # (d) 基于属性中引用的具名部件建立跨实体拓扑关联 (Domain Component Linking)
        name_to_iri: Dict[str, str] = {}
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
                            "type": ref_field.upper(),
                        })

        # 补充连边两端未显式声明的容器节点 (如 20231027_01 报告根节点)
        extra_nodes: Dict[str, Dict[str, Any]] = {}
        for e in edges:
            s_u = e["source"]
            t_u = e["target"]
            if s_u not in ind_nodes_dict and s_u not in classes_dict and s_u not in extra_nodes:
                s_name = s_u.split('/')[-1]
                extra_nodes[s_u] = {"iri": s_u, "name": s_name, "label": s_name, "primary_type": "ReportContainer", "attrs": {}}
            if t_u not in ind_nodes_dict and t_u not in classes_dict and t_u not in extra_nodes:
                t_name = t_u.split('/')[-1]
                extra_nodes[t_u] = {"iri": t_u, "name": t_name, "label": t_name, "primary_type": "Entity", "attrs": {}}

        all_nodes = list(classes_dict.values()) + list(ind_nodes_dict.values()) + list(extra_nodes.values())

        driver = self.get_driver()
        synced_nodes = 0
        synced_rels = 0

        try:
            with driver.session(database=self.database) as session:
                # 1. 确保唯一约束索引加速 MERGE
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.iri IS UNIQUE")

                # 2. 分批写入所有节点 (Batch size = 1000)
                batch_size = 1000
                cypher_fallback_nodes = """
                UNWIND $batch AS item
                MERGE (n:Entity {iri: item.iri})
                SET n.name = item.name,
                    n.label = item.label,
                    n.entity_type = item.primary_type,
                    n += item.attrs,
                    n.updated_at = datetime()
                RETURN count(n) AS cnt
                """
                for i in range(0, len(all_nodes), batch_size):
                    chunk = all_nodes[i : i + batch_size]
                    res = session.run(cypher_fallback_nodes, batch=chunk)
                    synced_nodes += res.single()["cnt"]

                # 3. 分批写入关系连边 (Batch size = 1000)
                cypher_links = """
                UNWIND $batch AS lk
                MATCH (a:Entity {iri: lk.source})
                MATCH (b:Entity {iri: lk.target})
                MERGE (a)-[r:RELATION {name: lk.type}]->(b)
                SET r.updated_at = datetime()
                RETURN count(r) AS cnt
                """
                for i in range(0, len(edges), batch_size):
                    chunk = edges[i : i + batch_size]
                    res_links = session.run(cypher_links, batch=chunk)
                    synced_rels += res_links.single()["cnt"]

            return {
                "success": True,
                "synced_nodes": synced_nodes,
                "synced_relationships": synced_rels,
                "total_entities_processed": len(all_nodes),
            }
        except Exception as e:
            logger.error(f"Sync to Neo4j failed: {e}")
            return {"success": False, "error": str(e)}


# 全局单例
neo4j_service = Neo4jKnowledgeService()
