import re, hashlib
from urllib.parse import quote, unquote

def resolve_individual_uri(ind_uri_str: str, ind_ns_str: str) -> str:
    # 提取末尾 local part
    raw_local = ind_uri_str.split("/")[-1].split("#")[-1]
    decoded = unquote(raw_local)
    parts = decoded.split("_")
    if len(parts) >= 3 and len(parts[-1]) in [6, 8, 10]:
        c_name = parts[0]
        raw_name = "_".join(parts[1:-1])
        # 执行走私串与键名清洗
        if ";" in raw_name:
            raw_name = raw_name.split(";")[0].strip()
        cleaned_name = re.sub(
            r"_(?:loop_type|key_components|component_type|safety_logic|maintenance_note|cooling_source|arrangement|key_feature).*",
            "",
            raw_name,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned_name:
            safe_slug = re.sub(r"[\s/\\\:\*\?\"\<\>\|\(\)\[\]\{\}]+", "_", cleaned_name).strip("_")[:36]
            h = hashlib.md5(f"{c_name}_{cleaned_name}".encode("utf-8")).hexdigest()[:8]
            return f"{ind_ns_str}{c_name}_{quote(safe_slug, safe='')}_{h}"
    return ind_uri_str

tests = [
    "https://w3id.org/ontogpt/auto_schema_309c131b/ind/AuxiliarySystem_%E6%B6%A6%E6%BB%91%E6%B2%B9%E7%B3%BB%E7%BB%9F%3B_loop_type_%3B_key_components_%3B_s_aa7955dd",
    "https://w3id.org/ontogpt/auto_schema_309c131b/ind/AuxiliarySystem_%E6%B6%A6%E6%BB%91%E6%B2%B9%E7%B3%BB%E7%BB%9F_470864c4",
    "https://w3id.org/ontogpt/auto_schema_309c131b/ind/AuxiliarySystem_%E6%B6%A6%E6%BB%91%E6%B2%B9%E7%B3%BB%E7%BB%9F_58f26261",
    "https://w3id.org/ontogpt/auto_schema_309c131b/ind/EquipmentComponent_%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F_fcb19ef7",
    "https://w3id.org/ontogpt/auto_schema_309c131b/ind/EquipmentComponent_%E5%8A%B1%E7%A3%81%E7%B3%BB%E7%BB%9F_b461c45a",
]

for t in tests:
    print(t.split('/')[-1], "-->", resolve_individual_uri(t, "https://w3id.org/ontogpt/auto_schema_309c131b/ind/").split('/')[-1])
