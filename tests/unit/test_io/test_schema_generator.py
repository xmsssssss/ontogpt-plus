"""Tests for LLM response parsing in the auto schema generator."""

import yaml
import pytest

from ontogpt.io.schema_generator import extract_yaml_from_response, sanitize_schema_id

SCHEMA_BODY = """id: https://w3id.org/ontogpt/demo
name: demo
title: Demo Schema
classes:
  DemoReport:
    tree_root: true
    attributes:
      id:
        identifier: true
"""


def test_complete_fence_with_surrounding_prose():
    raw = f"Here is the schema you asked for:\n\n```yaml\n{SCHEMA_BODY}```\n\nLet me know if you need changes."
    assert extract_yaml_from_response(raw).startswith("id:")


def test_fence_without_language_tag():
    raw = f"```\n{SCHEMA_BODY}```"
    assert extract_yaml_from_response(raw).startswith("id:")


def test_unterminated_fence_is_stripped():
    """响应被输出上限截断、缺少结尾围栏时，开头围栏行也必须剥掉。"""
    raw = f"```yaml\n{SCHEMA_BODY}"
    parsed = extract_yaml_from_response(raw)
    assert not parsed.startswith("```")
    assert parsed.startswith("id:")


def test_plain_yaml_with_leading_prose():
    raw = f"Sure! The schema is below.\n\n{SCHEMA_BODY}"
    assert extract_yaml_from_response(raw).startswith("id:")


def test_plain_yaml_without_prose():
    assert extract_yaml_from_response(SCHEMA_BODY).startswith("id:")


def test_stray_fence_lines_are_removed():
    raw = f"```yaml\n{SCHEMA_BODY}```\n```\n"
    assert "```" not in extract_yaml_from_response(raw)


def test_empty_response():
    assert extract_yaml_from_response("") == ""
    assert extract_yaml_from_response(None) == ""


@pytest.mark.parametrize(
    "raw",
    [
        f"```yaml\n{SCHEMA_BODY}```",
        f"```yaml\n{SCHEMA_BODY}",
        f"prose before\n{SCHEMA_BODY}",
        SCHEMA_BODY,
        f"```yaml\n{SCHEMA_BODY}```\n```\n",
    ],
)
def test_every_shape_is_loadable_yaml(raw):
    """回归：任何形态都必须能被 yaml.safe_load 解析，而不是抛 ScannerError。"""
    parsed = yaml.safe_load(extract_yaml_from_response(raw))
    assert isinstance(parsed, dict)
    assert parsed["name"] == "demo"
    assert "classes" in parsed


def test_sanitize_schema_id_ascii():
    assert sanitize_schema_id("hydro turbine") == "hydro_turbine"
    assert sanitize_schema_id("Battery-Storage") == "battery_storage"


def test_sanitize_schema_id_non_ascii_falls_back_to_hash():
    schema_id = sanitize_schema_id("水电站水轮机检修")
    assert schema_id.startswith("auto_schema_")
    assert len(schema_id) == len("auto_schema_") + 8


def test_format_discovered_features_for_prompt():
    from ontogpt.io.schema_generator import format_discovered_features_for_prompt

    raw_features = [
        {"key": "发电机定子温升", "value": "65K"},
        {"key": "发电机定子温升", "value": "68K"},
        {"key": "润滑油压", "value": "0.35MPa"},
    ]
    summary = format_discovered_features_for_prompt(raw_features)
    assert "发电机定子温升" in summary
    assert "润滑油压" in summary
    assert "65K" in summary
    assert "0.35MPa" in summary
    # 验证空处理
    assert format_discovered_features_for_prompt([]) == ""
    assert format_discovered_features_for_prompt(None) == ""


def test_in_flight_prompt_injection():
    from ontogpt.engines.spires_engine import SPIRESEngine
    from ontogpt.io.template_loader import get_template_details

    details = get_template_details("auto_schema_309c131b")
    engine = SPIRESEngine(template_details=details)
    engine.in_flight_features = {"绝缘油击穿电压", "定子温升"}
    prompt = engine.get_completion_prompt(text="测试文本")
    assert "auto_discovered_features" in prompt
    assert "绝缘油击穿电压" in prompt
    assert "定子温升" in prompt
