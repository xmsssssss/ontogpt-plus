"""Tests for W3C OWL 2 DL Builder and Extraction Quality Optimizer."""

import rdflib
import pytest
from rdflib import RDF, RDFS, OWL, XSD, URIRef, Literal, BNode

from ontogpt.io.owl_builder import OWL2Builder, clean_and_upgrade_owl_xml, is_noise_value, unpack_smuggled_string
from ontogpt.io.template_loader import get_template_details
from ontogpt.templates.core import ExtractionResult


def test_is_noise_value():
    assert is_noise_value("未明确指定") is True
    assert is_noise_value("null") is True
    assert is_noise_value("None") is True
    assert is_noise_value("N/A") is True
    assert is_noise_value("未提及") is True
    assert is_noise_value("未提供具体机理描述") is True
    assert is_noise_value("已配置/已具备") is True
    assert is_noise_value("无") is True
    # Genuine values must NOT be noise
    assert is_noise_value("离心式压缩机") is False
    assert is_noise_value("0.35MPa") is False
    assert is_noise_value("DL/T 1717-2017") is False


def test_unpack_smuggled_string():
    s = "凝结水排放; mechanism: 无; purpose: 排除多余水"
    unpacked = unpack_smuggled_string(s)
    assert unpacked["_main"] == "凝结水排放"
    assert unpacked["mechanism"] == "无"
    assert unpacked["purpose"] == "排除多余水"

    # Single string without semicolons
    assert unpack_smuggled_string("单纯过程名称") == {"_main": "单纯过程名称"}


def test_owl2_builder_generates_compliant_ontology():
    cls, py_mod, pyd_cls, sv = get_template_details("auto_schema_309c131b")
    sample = pyd_cls(
        id="test_doc_001",
        equipment_components=[
            {"name": "主变压器", "component_type": "核心电气设备", "cooling_source": "强油循环风冷"},
            {"name": "低压旁路阀", "component_type": "未明确指定", "key_feature": "null"},
        ],
        technical_processes=[
            {"process_name": "启动前暖管; mechanism: 逐步通入蒸汽加热管道; purpose: 避免水冲击", "control_method": "手动调节阀门"}
        ],
    )
    ann = ExtractionResult(extracted_object=sample)
    builder = OWL2Builder(schemaview=sv, schema_id="auto_schema_309c131b")
    g = builder.build_from_extraction(ann, id_value="test_doc_001")

    # 1. 验证存在且仅存在 1 个 owl:Ontology
    ontologies = list(g.subjects(RDF.type, OWL.Ontology))
    assert len(ontologies) == 1

    # 2. 验证所有 Class 均被声明为 owl:Class
    classes = list(g.subjects(RDF.type, OWL.Class))
    assert len(classes) >= 5

    # 3. 验证所有抽取出的实体均为 owl:NamedIndividual（零 Blank Nodes）
    named_inds = list(g.subjects(RDF.type, OWL.NamedIndividual))
    assert len(named_inds) >= 3  # Root report + 2 components + 1 process

    bnodes = [s for s in g.subjects() if isinstance(s, BNode)]
    assert len(bnodes) == 0

    # 4. 验证噪声数据未泄露
    for s, p, o in g:
        if isinstance(o, Literal):
            assert str(o) != "未明确指定"
            assert str(o) != "null"

    # 5. 验证串扰属性被解构为独立三元组
    predicates = [str(p) for s, p, o in g]
    assert any("purpose" in p for p in predicates)


def test_clean_and_upgrade_raw_owl_xml():
    raw_xml = """<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:demo="https://w3id.org/ontogpt/demo/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <demo:Report rdf:about="http://example.org/report1">
    <demo:components>
      <demo:Component rdf:nodeID="bnode1">
        <demo:name>测试泵</demo:name>
        <demo:feature>未明确指定</demo:feature>
      </demo:Component>
    </demo:components>
  </demo:Report>
</rdf:RDF>
"""
    upgraded = clean_and_upgrade_owl_xml(raw_xml, schema_id="demo")
    g = rdflib.Graph()
    g.parse(data=upgraded, format="xml")

    # 验证 BNode 已升级为具名个体
    bnodes = [s for s in g.subjects() if isinstance(s, BNode)]
    assert len(bnodes) == 0
    named_inds = list(g.subjects(RDF.type, OWL.NamedIndividual))
    assert len(named_inds) >= 1

    # 验证 "未明确指定" 已被清洗
    for s, p, o in g:
        if isinstance(o, Literal):
            assert str(o) != "未明确指定"
