"""
W3C OWL 2 DL Knowledge Ontology Builder & Quality Optimizer.

Transforms raw SPIRES extractions and LinkML structures into strictly compliant
W3C OWL 2 DL ontologies with:
1. Full TBox declarations (owl:Ontology, owl:Class, owl:ObjectProperty, owl:DatatypeProperty).
2. Elimination of anonymous blank nodes -> Deterministic, persistent owl:NamedIndividual IRIs.
3. Automated noise & placeholder trimming ("未明确指定", "null", "未提及", etc.).
4. In-flight slot de-smuggling (unpacking concatenated sub-slots like '; mechanism:').
"""

import hashlib
import logging
import re
from typing import Any, Dict, Optional, Set, Tuple, Union
from urllib.parse import quote, unquote

import pydantic
import rdflib
from linkml_runtime import SchemaView
from rdflib import BNode, Literal, Namespace, RDF, RDFS, OWL, XSD, URIRef

from ontogpt.templates.core import ExtractionResult

logger = logging.getLogger(__name__)

# 常见无信息量的空值/占位词过滤集合
NOISE_VALUES: Set[str] = {
    "未明确指定",
    "未明确",
    "未提及",
    "未提供",
    "未提供具体机理描述",
    "未提及具体机理",
    "未注明",
    "null",
    "none",
    "n/a",
    "na",
    "无",
    "暂无",
    "不详",
    "设联会提供",
    "已配置/已具备",
    "对应文本未直接提及",
    "文本未直接提及",
    "文中未直接提及",
    "文中未提及",
}

NOISE_REGEX = re.compile(
    r"^(未(明确|提及|提供|详|注明)|无(具体|特殊|要求|)|null|none|n/a)$",
    re.IGNORECASE,
)

SMUGGLED_PATTERN = re.compile(r";\s*([a-zA-Z_]+)\s*:")


def is_noise_value(val: Any) -> bool:
    """判断字面量是否为无意义的填充占位符。"""
    if val is None:
        return True
    s = str(val).strip()
    if not s:
        return True
    s_lower = s.lower()
    if s_lower in NOISE_VALUES or s in NOISE_VALUES:
        return True
    if NOISE_REGEX.match(s):
        return True
    return False


def clean_entity_identifier(raw_name: Optional[str]) -> str:
    """
    清洗大模型提取时泄露到实体标识名中的走私键名或串扰符号。
    例如: "润滑油系统;_loop_type_;_key_components_;_s" -> "润滑油系统"
          "燃机润滑油系统;_component_type_Lubrication__" -> "燃机润滑油系统"
    """
    if not raw_name:
        return ""
    name = str(raw_name).strip()
    if ";" in name:
        name = name.split(";")[0].strip()
    name = re.sub(
        r"_(?:loop_type|key_components|component_type|safety_logic|maintenance_note|cooling_source|arrangement|key_feature).*",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
    return name


def unpack_smuggled_string(s: str) -> Dict[str, str]:
    """
    解构模型误将多个子槽位拼接在单行文本中的串扰数据。
    例如: "凝结水排放; mechanism: 无; purpose: 排除多余凝结水"
    返回: {"_main": "凝结水排放", "mechanism": "无", "purpose": "排除多余凝结水"}
    """
    if not s or ";" not in s:
        return {"_main": s}

    parts = s.split(";")
    result: Dict[str, str] = {}
    main_val = parts[0].strip()
    result["_main"] = main_val

    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k and v:
                result[k] = v
        elif "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k and v:
                result[k] = v

    return result


class OWL2Builder:
    """W3C OWL 2 DL 知识图谱与本体构建器。"""

    def __init__(
        self,
        schemaview: Optional[SchemaView] = None,
        base_uri: Optional[str] = None,
        schema_id: Optional[str] = None,
    ):
        self.schemaview = schemaview
        self.schema_id = schema_id or "knowledge_ontology"
        if base_uri:
            self.base_uri = base_uri.rstrip("/") + "/"
        elif schemaview and getattr(schemaview.schema, "id", None):
            self.base_uri = schemaview.schema.id.rstrip("/") + "/"
        else:
            self.base_uri = f"https://w3id.org/ontogpt/{self.schema_id}/"

        self.ns = Namespace(self.base_uri)
        self.ind_ns = Namespace(self.base_uri + "ind/")

    def _generate_individual_uri(self, class_name: str, name_or_key: Optional[str], raw_dict: Dict[str, Any]) -> URIRef:
        """
        为实体生成有意义、全局稳定且支持跨分片自动融合的唯一 IRI（Entity Resolution）。
        同 Class 且同业务名的实体自动对齐到相同的持久 IRI。
        """
        candidate = clean_entity_identifier(name_or_key) or ""
        if not candidate:
            for k in ["name", "key", "process_name", "parameter_name", "system_name", "id"]:
                val = raw_dict.get(k)
                if val and not is_noise_value(val):
                    candidate = clean_entity_identifier(str(val))
                    if candidate:
                        break

        if candidate and not is_noise_value(candidate):
            # 清理非法字符用于生成易读的 IRI fragment
            safe_slug = re.sub(r"[\s/\\\:\*\?\"\<\>\|\(\)\[\]\{\}]+", "_", candidate).strip("_")
            safe_slug = safe_slug[:36]
            # 跨分片对齐：根据 (class_name, candidate) 确定唯一实体标识，支持属性合并
            h = hashlib.md5(f"{class_name}_{candidate}".encode("utf-8")).hexdigest()[:8]
            return self.ind_ns[f"{class_name}_{quote(safe_slug, safe='')}_{h}"]
        else:
            h = hashlib.md5(f"{class_name}_{sorted(raw_dict.items())}".encode("utf-8")).hexdigest()[:10]
            return self.ind_ns[f"{class_name}_{h}"]

    def build_from_extraction(
        self,
        extraction_output: ExtractionResult,
        id_value: Optional[str] = None,
    ) -> rdflib.Graph:
        """将 ExtractionResult 转化为符合 W3C OWL 2 DL 标准的 RDFLib Graph。"""
        g = rdflib.Graph()
        g.bind("owl", OWL)
        g.bind("rdf", RDF)
        g.bind("rdfs", RDFS)
        g.bind("xsd", XSD)
        g.bind(self.schema_id, self.ns)
        g.bind("ind", self.ind_ns)

        # 1. 声明 owl:Ontology
        ont_uri = URIRef(self.base_uri.rstrip("/"))
        g.add((ont_uri, RDF.type, OWL.Ontology))
        ont_title = getattr(self.schemaview.schema, "title", None) if self.schemaview else None
        ont_title = ont_title or f"{self.schema_id} W3C OWL 2 Knowledge Ontology"
        g.add((ont_uri, RDFS.label, Literal(ont_title, lang="zh")))
        ont_desc = getattr(self.schemaview.schema, "description", None) if self.schemaview else None
        ont_desc = ont_desc or "Automated semantic extraction knowledge ontology generated by OntoGPT."
        g.add((ont_uri, RDFS.comment, Literal(ont_desc, lang="zh")))
        g.add((ont_uri, OWL.versionInfo, Literal("2.0.0")))

        # 2. 注入 TBox（类定义与属性定义）
        declared_classes: Set[str] = set()
        declared_props: Set[str] = set()

        if self.schemaview:
            for c_name, c_def in self.schemaview.all_classes().items():
                c_uri = self.ns[c_name]
                g.add((c_uri, RDF.type, OWL.Class))
                declared_classes.add(c_name)
                if c_def.description:
                    g.add((c_uri, RDFS.comment, Literal(c_def.description)))
                g.add((c_uri, RDFS.label, Literal(c_name)))
                if c_def.is_a:
                    g.add((c_uri, RDFS.subClassOf, self.ns[c_def.is_a]))

            for s_name, s_def in self.schemaview.all_slots().items():
                s_uri = self.ns[s_name]
                declared_props.add(s_name)
                is_obj_prop = s_def.range in self.schemaview.all_classes()
                if is_obj_prop:
                    g.add((s_uri, RDF.type, OWL.ObjectProperty))
                    g.add((s_uri, RDFS.range, self.ns[s_def.range]))
                    # 映射 OWL 2 对象属性特征 (Property Characteristics)
                    if getattr(s_def, "transitive", False):
                        g.add((s_uri, RDF.type, OWL.TransitiveProperty))
                    if getattr(s_def, "symmetric", False):
                        g.add((s_uri, RDF.type, OWL.SymmetricProperty))
                    if getattr(s_def, "asymmetric", False):
                        g.add((s_uri, RDF.type, OWL.AsymmetricProperty))
                    if getattr(s_def, "reflexive", False):
                        g.add((s_uri, RDF.type, OWL.ReflexiveProperty))
                    if getattr(s_def, "irreflexive", False):
                        g.add((s_uri, RDF.type, OWL.IrreflexiveProperty))
                else:
                    g.add((s_uri, RDF.type, OWL.DatatypeProperty))
                    g.add((s_uri, RDFS.range, XSD.string))

                # 单值属性映射为 FunctionalProperty (函数型/单值约束)
                if not getattr(s_def, "multivalued", False):
                    g.add((s_uri, RDF.type, OWL.FunctionalProperty))

                if s_def.description:
                    g.add((s_uri, RDFS.comment, Literal(s_def.description)))
                g.add((s_uri, RDFS.label, Literal(s_name)))

        # 3. 注入 ABox（具名个体实例）
        root_obj = extraction_output.extracted_object
        if not root_obj:
            return g

        root_dict = root_obj.model_dump() if hasattr(root_obj, "model_dump") else dict(root_obj)
        root_cls_name = type(root_obj).__name__
        root_id = id_value or root_dict.get("id") or "ROOT_RECORD"
        root_uri = self.ind_ns[f"Report_{quote(str(root_id), safe='')}"]

        g.add((root_uri, RDF.type, OWL.NamedIndividual))
        g.add((root_uri, RDF.type, self.ns[root_cls_name]))
        g.add((root_uri, RDFS.label, Literal(f"Report: {root_id}")))

        # 递归处理根对象各属性与实体列表
        self._populate_properties(g, root_uri, root_dict, root_cls_name, declared_classes, declared_props)

        return g

    def _populate_properties(
        self,
        g: rdflib.Graph,
        subj_uri: URIRef,
        data_dict: Dict[str, Any],
        class_name: str,
        declared_classes: Set[str],
        declared_props: Set[str],
    ) -> None:
        """递归填充属性、个体并清洗占位符。"""
        for k, v in data_dict.items():
            if k == "id" or v is None:
                continue

            prop_uri = self.ns[k]
            if k not in declared_props:
                # 动态自适应补全
                declared_props.add(k)
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    g.add((prop_uri, RDF.type, OWL.ObjectProperty))
                else:
                    g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                g.add((prop_uri, RDFS.label, Literal(k)))

            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        # 判断该子对象类型
                        item_cls = self._guess_class_name(k, item)
                        item_uri = self._generate_individual_uri(item_cls, item.get("name") or item.get("key"), item)

                        # 检查子对象是否全为空
                        valid_items = {ik: iv for ik, iv in item.items() if not is_noise_value(iv)}
                        if not valid_items:
                            continue

                        # 声明为具名实体
                        g.add((item_uri, RDF.type, OWL.NamedIndividual))
                        g.add((item_uri, RDF.type, self.ns[item_cls]))
                        label_val = valid_items.get("name") or valid_items.get("key") or valid_items.get("process_name") or valid_items.get("parameter_name")
                        if label_val:
                            g.add((item_uri, RDFS.label, Literal(str(label_val))))

                        # 主对象通过对象属性指向该具名个体
                        g.add((subj_uri, prop_uri, item_uri))

                        # 填充子个体的属性并解构串扰
                        self._fill_individual_attributes(g, item_uri, valid_items, declared_props)
                    elif isinstance(item, (str, int, float, bool)):
                        if not is_noise_value(item):
                            g.add((subj_uri, prop_uri, Literal(str(item))))
            elif isinstance(v, dict):
                item_cls = self._guess_class_name(k, v)
                item_uri = self._generate_individual_uri(item_cls, v.get("name"), v)
                valid_items = {ik: iv for ik, iv in v.items() if not is_noise_value(iv)}
                if valid_items:
                    g.add((item_uri, RDF.type, OWL.NamedIndividual))
                    g.add((item_uri, RDF.type, self.ns[item_cls]))
                    g.add((subj_uri, prop_uri, item_uri))
                    self._fill_individual_attributes(g, item_uri, valid_items, declared_props)
            else:
                if not is_noise_value(v):
                    g.add((subj_uri, prop_uri, Literal(str(v))))

    def _fill_individual_attributes(
        self,
        g: rdflib.Graph,
        ind_uri: URIRef,
        valid_items: Dict[str, Any],
        declared_props: Set[str],
    ) -> None:
        """为具名个体填充属性，并解构串扰子槽位。"""
        for attr_k, attr_v in valid_items.items():
            if attr_v is None or is_noise_value(attr_v):
                continue

            attr_str = str(attr_v).strip()
            # 检查是否有串扰（例如 "过程名; mechanism: xx; purpose: yy"）
            unpacked = unpack_smuggled_string(attr_str)
            main_val = unpacked.pop("_main", attr_str)

            if not is_noise_value(main_val):
                p_uri = self.ns[attr_k]
                g.add((ind_uri, p_uri, Literal(main_val)))

            # 将解构出来的子槽位提升为规范属性
            for extra_k, extra_v in unpacked.items():
                if not is_noise_value(extra_v):
                    sub_p_uri = self.ns[extra_k]
                    g.add((ind_uri, sub_p_uri, Literal(extra_v)))
                    if extra_k not in declared_props:
                        declared_props.add(extra_k)
                        g.add((sub_p_uri, RDF.type, OWL.DatatypeProperty))
                        g.add((sub_p_uri, RDFS.label, Literal(extra_k)))

    def _guess_class_name(self, slot_name: str, item_dict: Dict[str, Any]) -> str:
        """推断或获取子对象的类名。"""
        if self.schemaview:
            slot_def = self.schemaview.get_slot(slot_name)
            if slot_def and slot_def.range in self.schemaview.all_classes():
                return slot_def.range

        # 启发式按属性单复数推断
        if slot_name.endswith("ies"):
            base = slot_name[:-3] + "y"
        elif slot_name.endswith("s"):
            base = slot_name[:-1]
        else:
            base = slot_name

        words = base.split("_")
        return "".join(w.capitalize() for w in words)


def clean_and_upgrade_owl_xml(
    raw_owl_xml: str,
    schemaview: Optional[SchemaView] = None,
    schema_id: Optional[str] = None,
) -> str:
    """
    接收已存在的 raw RDF/OWL XML 字符串，执行全面清洗并升级为合规 W3C OWL 2 DL XML：
    1. 注入 owl:Ontology 声明与元数据。
    2. 补全 owl:Class、owl:ObjectProperty、owl:DatatypeProperty TBox。
    3. 将全部匿名空白节点 (Blank Nodes) 升格为 owl:NamedIndividual。
    4. 清除全部“未明确指定”、“null”等垃圾三元组。
    5. 解构字段内部的串扰子槽位。
    """
    if not raw_owl_xml or "<rdf:RDF" not in raw_owl_xml:
        return raw_owl_xml

    g_in = rdflib.Graph()
    try:
        g_in.parse(data=raw_owl_xml, format="xml")
    except Exception as e:
        logger.warning(f"Failed to parse input OWL XML for upgrade: {e}")
        return raw_owl_xml

    # 自动探测主命名空间
    detected_schema_id = schema_id or "knowledge_ontology"
    schema_ns_uri = None
    for prefix, ns in g_in.namespaces():
        if "ontogpt" in str(ns) or "auto_schema" in str(ns) or prefix in ["power_grid", "drug"]:
            detected_schema_id = prefix
            schema_ns_uri = str(ns)
            break

    if not schema_ns_uri:
        schema_ns_uri = f"https://w3id.org/ontogpt/{detected_schema_id}/"

    base_uri = schema_ns_uri.rstrip("/") + "/"
    ind_base_uri = base_uri + "ind/"

    g_out = rdflib.Graph()
    g_out.bind("owl", OWL)
    g_out.bind("rdf", RDF)
    g_out.bind("rdfs", RDFS)
    g_out.bind("xsd", XSD)
    g_out.bind(detected_schema_id, Namespace(base_uri))
    g_out.bind("ind", Namespace(ind_base_uri))

    # 1. 声明 owl:Ontology
    ont_uri = URIRef(base_uri.rstrip("/"))
    g_out.add((ont_uri, RDF.type, OWL.Ontology))
    g_out.add((ont_uri, RDFS.label, Literal(f"{detected_schema_id} W3C OWL 2 Ontology", lang="zh")))
    g_out.add((ont_uri, RDFS.comment, Literal("Cleaned, upgraded and W3C OWL 2 DL compliant ontology.", lang="zh")))
    g_out.add((ont_uri, OWL.versionInfo, Literal("2.0.0")))

    # 2. 收集所有使用的 Class 与 Predicate，注入 TBox
    classes_used: Set[URIRef] = set()
    predicates_used: Set[URIRef] = set()
    for s, p, o in g_in:
        if p == RDF.type and isinstance(o, URIRef) and o not in [OWL.NamedIndividual, OWL.Class]:
            classes_used.add(o)
        if p not in [RDF.type]:
            predicates_used.add(p)

    for c in classes_used:
        g_out.add((c, RDF.type, OWL.Class))
        c_label = str(c).rstrip("/").split("/")[-1].split("#")[-1]
        g_out.add((c, RDFS.label, Literal(c_label)))

    # 3. 将 Blank Nodes 与已存在实体映射到对齐后的标准具名 IRI (Entity Resolution)
    ind_map: Dict[Union[BNode, URIRef], URIRef] = {}
    ind_ns = Namespace(ind_base_uri)
    schema_ns = Namespace(base_uri)

    for s in set(g_in.subjects()):
        if isinstance(s, BNode):
            c_type = g_in.value(s, RDF.type)
            c_name = str(c_type).rstrip("/").split("/")[-1].split("#")[-1] if c_type else "Entity"
            # 寻找该个体的标识名并执行走私字段剥离
            id_name = None
            for name_field in ["name", "key", "process_name", "parameter_name", "system_name"]:
                candidate = g_in.value(s, schema_ns[name_field])
                if candidate and not is_noise_value(str(candidate)):
                    cleaned_candidate = clean_entity_identifier(str(candidate))
                    if cleaned_candidate and not is_noise_value(cleaned_candidate):
                        id_name = cleaned_candidate
                        break

            if id_name:
                safe_slug = re.sub(r"[\s/\\\:\*\?\"\<\>\|\(\)\[\]\{\}]+", "_", id_name).strip("_")[:36]
                # 实体对齐：基于 (c_name, id_name) 对齐到同一 URI，合并多处提及
                h = hashlib.md5(f"{c_name}_{id_name}".encode("utf-8")).hexdigest()[:8]
                ind_uri = ind_ns[f"{c_name}_{quote(safe_slug, safe='')}_{h}"]
            else:
                h = hashlib.md5(f"{c_name}_{s}".encode("utf-8")).hexdigest()[:10]
                ind_uri = ind_ns[f"{c_name}_{h}"]

            ind_map[s] = ind_uri
        elif isinstance(s, URIRef) and str(s).startswith(ind_base_uri):
            # 对已有具名个体也做对齐与走私字符串清洗
            s_str = str(s)
            raw_local = s_str.split("/")[-1].split("#")[-1]
            decoded = unquote(raw_local)
            parts = decoded.split("_")
            if len(parts) >= 3 and len(parts[-1]) in [6, 8, 10]:
                c_name = parts[0]
                raw_name = "_".join(parts[1:-1])
                cleaned_name = clean_entity_identifier(raw_name)
                if cleaned_name and not is_noise_value(cleaned_name):
                    safe_slug = re.sub(r"[\s/\\\:\*\?\"\<\>\|\(\)\[\]\{\}]+", "_", cleaned_name).strip("_")[:36]
                    h = hashlib.md5(f"{c_name}_{cleaned_name}".encode("utf-8")).hexdigest()[:8]
                    ind_map[s] = ind_ns[f"{c_name}_{quote(safe_slug, safe='')}_{h}"]

    # 4. 迁移三元组并过滤清洗
    single_val_tracker: Dict[Tuple[URIRef, URIRef], int] = {}
    obj_props_seen: Set[URIRef] = set()
    data_props_seen: Set[URIRef] = set()

    for s, p, o in g_in:
        # 解析主体
        new_s = ind_map.get(s, s)

        # 解析客体
        if isinstance(o, (BNode, URIRef)) and o in ind_map:
            new_o = ind_map[o]
            g_out.add((new_s, p, new_o))
            obj_props_seen.add(p)
            single_val_tracker[(new_s, p)] = single_val_tracker.get((new_s, p), 0) + 1
        elif isinstance(o, Literal):
            lit_val = str(o).strip()
            if is_noise_value(lit_val):
                continue

            # 拆解串扰字段并清洗键名泄露
            unpacked = unpack_smuggled_string(lit_val)
            main_val = clean_entity_identifier(unpacked.pop("_main", lit_val))

            if not is_noise_value(main_val):
                g_out.add((new_s, p, Literal(main_val)))
                data_props_seen.add(p)
                single_val_tracker[(new_s, p)] = single_val_tracker.get((new_s, p), 0) + 1

            for sub_k, sub_v in unpacked.items():
                clean_sub_v = clean_entity_identifier(sub_v)
                if not is_noise_value(clean_sub_v) and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{1,32}$", sub_k):
                    sub_p = schema_ns[sub_k]
                    g_out.add((new_s, sub_p, Literal(clean_sub_v)))
                    data_props_seen.add(sub_p)
                    single_val_tracker[(new_s, sub_p)] = single_val_tracker.get((new_s, sub_p), 0) + 1
        else:
            g_out.add((new_s, p, o))

    # 声明对象属性与数据属性，并推导注入 OWL 特征 (Characteristics)
    for p in obj_props_seen:
        g_out.add((p, RDF.type, OWL.ObjectProperty))
        p_name = str(p).split("/")[-1].split("#")[-1].lower()
        if any(tk in p_name for tk in ["part_of", "sub_system", "subsystem", "component_of", "contain"]):
            g_out.add((p, RDF.type, OWL.TransitiveProperty))
        if any(tk in p_name for tk in ["connected", "adjacent", "linked", "coupled"]):
            g_out.add((p, RDF.type, OWL.SymmetricProperty))

    for p in data_props_seen:
        g_out.add((p, RDF.type, OWL.DatatypeProperty))

    # 统计单值属性以断言 FunctionalProperty
    multi_valued_props: Set[URIRef] = set()
    for (subj, prop), count in single_val_tracker.items():
        if count > 1:
            multi_valued_props.add(prop)

    for p in (obj_props_seen | data_props_seen):
        if p not in multi_valued_props:
            p_name = str(p).split("/")[-1].split("#")[-1].lower()
            if not p_name.endswith("s") and not any(k in p_name for k in ["list", "features", "actions"]):
                g_out.add((p, RDF.type, OWL.FunctionalProperty))

    # 5. 为所有具名个体补充 owl:NamedIndividual 声明与 rdfs:label
    for s in set(g_out.subjects()):
        if isinstance(s, URIRef) and str(s).startswith(ind_base_uri):
            g_out.add((s, RDF.type, OWL.NamedIndividual))
            if not list(g_out.objects(s, RDFS.label)):
                local_name = str(s).split("/")[-1]
                g_out.add((s, RDFS.label, Literal(local_name)))

    # 导出序列化为标准 pretty-xml
    return g_out.serialize(format="pretty-xml", encoding="utf-8").decode("utf-8")
