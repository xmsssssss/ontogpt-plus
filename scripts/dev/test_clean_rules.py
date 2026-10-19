import re

SMUGGLED_KEYWORD_RE = re.compile(
    r";\s*([a-zA-Z_]+)\s*[:=]|"
    r"_[a-z]+_[a-z]+_|;\s*[a-z_]+;|\b(?:loop_type|key_components|component_type|safety_logic|maintenance_note)\b",
    re.IGNORECASE
)

test_names = [
    "润滑油系统;_loop_type_;_key_components_;_s",
    "燃机润滑油系统;_component_type_Lubrication__",
    "润滑油系统;loop_type_未提及;key_components_油",
    "主变压器",
    "高起始响应静止励磁系统",
    "FCB励磁开关",
    "温度",
    "压力",
    "流量",
    "未识别参数",
    "auto_discovered_features"
]

def clean_entity_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    # 截断分号后面的任何拼接键名或内容
    name = raw_name.split(";")[0].strip()
    # 清理常见的下划线键名泄漏
    name = re.sub(r"_(?:loop_type|key_components|component_type|safety_logic|maintenance_note|cooling_source|arrangement|key_feature).*", "", name, flags=re.IGNORECASE).strip()
    return name

for t in test_names:
    print(f"Original: {t!r:45} -> Cleaned: {clean_entity_name(t)!r}")
