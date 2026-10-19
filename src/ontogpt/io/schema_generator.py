import importlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml
from linkml.generators.pydanticgen import PydanticGenerator
from linkml_runtime import SchemaView

from ontogpt.io.template_loader import get_template_details
from ontogpt.io.utils import ensure_utf8_coding_cookie

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def sanitize_schema_id(text: str) -> str:
    """Generate a clean snake_case identifier."""
    # If contains Chinese or non-ascii, romanize or hash
    cleaned = re.sub(r"[^\w\s-]", "", text).strip()
    cleaned = re.sub(r"[-\s]+", "_", cleaned).lower()
    # If cleaned is non-ascii or empty, generate a fallback
    if not cleaned or not re.match(r"^[a-z][a-z0-9_]*$", cleaned):
        import hashlib
        short_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        return f"auto_schema_{short_hash}"
    return cleaned[:30]


SCHEMA_PROMPT_TEMPLATE = """You are a senior Knowledge Graph & Ontology Engineer specializing in LinkML (Linked Data Modeling Language) and W3C OWL.
Your task is to analyze the user's provided domain description and sample text, and automatically design a professional, production-grade LinkML YAML Schema for structured information extraction.

Domain / Topic: {domain_hint}

Sample Text from this domain:
\"\"\"
{sample_text}
\"\"\"

Requirements for the generated LinkML Schema:
1. Output MUST BE ONLY valid LinkML YAML syntax inside ```yaml ... ``` code fence. No explanations before or after.
2. The schema must include:
   id: https://w3id.org/ontogpt/{schema_id}
   name: {schema_id}
   title: <Concise English Title>
   description: <Concise Chinese and English description of the domain>
   default_prefix: {schema_id}
   default_range: string
   prefixes:
     linkml: https://w3id.org/linkml/
     core: https://w3id.org/ontogpt/core/
     {schema_id}: https://w3id.org/ontogpt/{schema_id}/
   imports:
     - linkml:types
     - core

3. Classes Structure:
   - Exactly ONE Root Class (e.g. `{root_class_name}`) marked with `tree_root: true`.
     - It MUST have an `id` attribute:
       id:
         identifier: true
         range: string
         description: Unique auto identifier
     - It should have 3 to 6 domain-specific multivalued slots pointing to compound classes (e.g., equipment, processes, parameters, events, actions).
     - It MUST also include a fallback slot:
       auto_discovered_features:
         multivalued: true
         range: KeyValuePair
         description: 动态未归类特征键值对
   - 3 to 6 Compound Expression Classes (each with `is_a: CompoundExpression`), describing key domain entities or events with specific attributes and clear descriptions.
   - Include the helper class:
     KeyValuePair:
       is_a: CompoundExpression
       description: 自适应发现的专有属性键值对
       attributes:
         key:
           description: 属性或参量名称
         value:
           description: 属性取值及单位

4. Attributes & Characteristics Guidelines:
   - For multivalued slots pointing to multiple items, set `multivalued: true`.
   - For single-valued properties (e.g. name, rated values), keep `multivalued: false` (automatically mapped to OWL FunctionalProperty).
   - If an object relationship expresses hierarchical containment (like sub-components or part_of), explicitly specify `transitive: true` (mapped to OWL TransitiveProperty).
   - If a relationship is mutually reciprocal (like connected_to, adjacent_to), explicitly specify `symmetric: true` (mapped to OWL SymmetricProperty).
   - Write informative Chinese descriptions in the `description:` of every attribute, explaining what text patterns the LLM should extract.

Now output ONLY the raw YAML schema:
"""


def build_schema_prompt(sample_text: str, domain_hint: str, schema_id: str) -> str:
    # Capitalized root class name
    words = schema_id.split("_")
    root_class_name = "".join(w.capitalize() for w in words) + "Report"
    return SCHEMA_PROMPT_TEMPLATE.format(
        domain_hint=domain_hint or "专业工程领域文档",
        sample_text=sample_text[:2500],
        schema_id=schema_id,
        root_class_name=root_class_name,
    )


FENCED_BLOCK_RE = re.compile(
    r"```[ \t]*(?P<lang>[A-Za-z0-9_+.-]*)[ \t]*\r?\n(?P<body>.*?)\r?\n?```",
    re.DOTALL,
)
OPENING_FENCE_RE = re.compile(r"\A[ \t]*```[A-Za-z0-9_+.-]*[ \t]*\r?\n")
YAML_TOP_LEVEL_KEY_RE = re.compile(
    r"^(?:id|name|title|description|default_range|default_prefix|prefixes|imports"
    r"|classes|slots|enums|subsets|types)\s*:",
    re.MULTILINE,
)


def _drop_fence_lines(text: str) -> str:
    """Remove leftover ``` fence markers so the payload is safe to parse."""
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _trim_to_document_start(text: str) -> str:
    """Drop leading prose so the payload begins at a plausible top-level YAML key."""
    match = YAML_TOP_LEVEL_KEY_RE.search(text)
    if match:
        return text[match.start() :]
    return text


def extract_yaml_from_response(raw_text: str) -> str:
    """Extract a clean YAML payload from an LLM response.

    A well-formed ```yaml fence is only one of several shapes a model returns:

    * a complete fence, optionally surrounded by prose;
    * an opening fence whose closing fence was cut off by the provider's output
      token limit - the old implementation missed this case, fell back to
      returning the raw response with the fence line included, and then failed
      inside ``yaml.safe_load`` with a ScannerError on the leading backticks;
    * no fence at all, with explanatory prose wrapped around the document.

    Any stray fence markers left behind are stripped, so the returned string is
    always safe to hand to ``yaml.safe_load``.
    """
    text = (raw_text or "").strip()
    if not text:
        return ""

    blocks = [
        ((match.group("lang") or "").lower(), (match.group("body") or "").strip())
        for match in FENCED_BLOCK_RE.finditer(text)
    ]
    for lang, body in blocks:
        if body and lang in ("", "yaml", "yml"):
            return _drop_fence_lines(body)
    for _lang, body in blocks:
        if body:
            return _drop_fence_lines(body)

    if OPENING_FENCE_RE.match(text):
        # 结尾围栏缺失：剥掉开头围栏行，其余整体视为载荷
        return _drop_fence_lines(OPENING_FENCE_RE.sub("", text, count=1).strip())

    return _drop_fence_lines(_trim_to_document_start(text))


def compile_and_register_schema(
    schema_id: str,
    yaml_content: str,
) -> Dict[str, Any]:
    """Validate, compile to Pydantic Python module, and register the new schema."""
    try:
        parsed = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        preview = next((line for line in (yaml_content or "").splitlines() if line.strip()), "")
        raise ValueError(
            f"模型返回的内容无法解析为 YAML（首行：{preview[:120]}）。"
            "通常是输出被截断或混入了说明文字，请重试或换用输出上限更高的模型。"
        ) from exc
    if not isinstance(parsed, dict) or "classes" not in parsed:
        raise ValueError(
            "生成的内容不是合法的 LinkML YAML Schema（缺少 classes 定义）。"
            "若模型输出较长，可能是响应被输出上限截断，请重试或换用输出上限更高的模型。"
        )

    # Ensure imports contains linkml:types and core
    imports = parsed.get("imports", [])
    if "core" not in imports:
        imports.append("core")
    if "linkml:types" not in imports:
        imports.append("linkml:types")
    parsed["imports"] = imports

    # Ensure tree_root: true exists on one class
    classes = parsed.get("classes", {})
    root_count = sum(1 for c in classes.values() if isinstance(c, dict) and c.get("tree_root"))
    if root_count == 0:
        # Set first class as root
        first_cls_name = next(iter(classes.keys()))
        classes[first_cls_name]["tree_root"] = True
    elif root_count > 1:
        # Keep only the first one
        found = False
        for c in classes.values():
            if isinstance(c, dict) and c.get("tree_root"):
                if found:
                    c["tree_root"] = False
                found = True

    # Ensure KeyValuePair class exists
    if "KeyValuePair" not in classes:
        classes["KeyValuePair"] = {
            "is_a": "CompoundExpression",
            "description": "自适应发现的专有属性键值对",
            "attributes": {
                "key": {"description": "属性或参量名称"},
                "value": {"description": "属性取值及单位"},
            },
        }

    # Ensure Root Class has auto_discovered_features slot
    for c_name, c_def in classes.items():
        if isinstance(c_def, dict) and c_def.get("tree_root"):
            attrs = c_def.setdefault("attributes", {})
            if "id" not in attrs:
                attrs["id"] = {"identifier": True, "range": "string", "description": "唯一根标识"}
            if "auto_discovered_features" not in attrs:
                attrs["auto_discovered_features"] = {
                    "multivalued": True,
                    "range": "KeyValuePair",
                    "description": "自适应提取的专有特征",
                }
            break

    # Re-dump validated YAML
    cleaned_yaml = yaml.dump(parsed, allow_unicode=True, sort_keys=False)

    yaml_file = TEMPLATES_DIR / f"{schema_id}.yaml"
    py_file = TEMPLATES_DIR / f"{schema_id}.py"

    yaml_file.write_text(cleaned_yaml, encoding="utf-8")

    # Compile with PydanticGenerator
    gen = PydanticGenerator(str(yaml_file))
    py_code = ensure_utf8_coding_cookie(gen.serialize())
    py_file.write_text(py_code, encoding="utf-8")

    # Invalidate import caches and verify import
    importlib.invalidate_caches()
    cls, mod, pyclass, sv = get_template_details(schema_id)

    class_names = list(classes.keys())
    return {
        "success": True,
        "schema_id": schema_id,
        "title": parsed.get("title", schema_id),
        "description": parsed.get("description", ""),
        "classes": class_names,
        "root_class": cls.name,
        "yaml_content": cleaned_yaml,
    }


EVOLVE_SCHEMA_PROMPT_TEMPLATE = """You are a senior Knowledge Graph & Ontology Engineer specializing in LinkML (Linked Data Modeling Language) and W3C OWL.
We have an existing production LinkML Schema for domain: '{schema_id}'.

During automated information extraction on technical documents, the system dynamically captured the following domain-specific properties, parameters, or key-value pairs that were not explicitly covered as first-class slots in the current schema:

Discovered unclassified parameters & features:
{features_summary}

Current LinkML YAML Schema:
```yaml
{current_yaml}
```

Task Requirements for Schema Evolution:
1. Analyze the newly discovered parameters, group or generalize them appropriately into formal domain concepts, and EVOLVE the LinkML schema.
2. Upgrade frequent or significant discovered features into dedicated attributes/slots within existing classes, or create 1~2 new compound classes (`is_a: CompoundExpression`) if a new distinct entity type is identified.
3. PRESERVE all existing classes, slot names, imports (`linkml:types`, `core`), prefixes, and the `tree_root: true` class. Do not break or delete existing fields!
4. MUST RETAIN the fallback slot `auto_discovered_features: KeyValuePair` and helper class `KeyValuePair` on the root class for future unknown features.
5. Write clear Chinese descriptions in `description:` for every newly added slot or class, explaining what domain information it extracts.
6. Enrich relationships with OWL characteristics where appropriate: use `transitive: true` for hierarchy/sub-part slots, `symmetric: true` for mutual connections, and ensure single-valued attributes keep `multivalued: false`.
7. Output MUST BE ONLY the complete, updated valid LinkML YAML syntax inside ```yaml ... ``` code fence. No explanations before or after.

Now output ONLY the evolved LinkML YAML schema:
"""


def format_discovered_features_for_prompt(features: Any, max_items: int = 35) -> str:
    """Format and deduplicate captured KeyValuePair features into a readable summary."""
    if not features:
        return ""

    seen_keys: Dict[str, List[str]] = {}
    for feat in features:
        if isinstance(feat, dict):
            k = feat.get("key") or ""
            v = feat.get("value") or ""
        else:
            k = getattr(feat, "key", "") or ""
            v = getattr(feat, "value", "") or ""
        k = str(k).strip()
        v = str(v).strip()
        if k:
            if k not in seen_keys:
                seen_keys[k] = []
            if v and v not in seen_keys[k] and len(seen_keys[k]) < 3:
                seen_keys[k].append(v)

    if not seen_keys:
        return ""

    lines = []
    for k, sample_vals in list(seen_keys.items())[:max_items]:
        val_str = f" (取值示例: {', '.join(sample_vals)})" if sample_vals else ""
        lines.append(f"- 特征参数: {k}{val_str}")
    return "\n".join(lines)


def auto_evolve_schema_with_features(
    schema_id: str,
    discovered_features: Any,
    client: Any,
) -> Dict[str, Any]:
    """Analyze dynamically discovered features, update the schema YAML, recompile, and register."""
    yaml_file = TEMPLATES_DIR / f"{schema_id}.yaml"
    if not yaml_file.exists():
        return {
            "success": False,
            "evolved": False,
            "error": f"本地模板模式文件不存在: {yaml_file.name}",
        }

    features_summary = format_discovered_features_for_prompt(discovered_features)
    if not features_summary:
        return {
            "success": True,
            "evolved": False,
            "message": "未捕获到新增的未归类特征，Schema 无需更新。",
        }

    current_yaml = yaml_file.read_text(encoding="utf-8")

    prompt = EVOLVE_SCHEMA_PROMPT_TEMPLATE.format(
        schema_id=schema_id,
        features_summary=features_summary,
        current_yaml=current_yaml[:6000],
    )

    try:
        raw_response = client.complete(prompt=prompt, max_tokens=8192)
        evolved_yaml = extract_yaml_from_response(raw_response)
        result = compile_and_register_schema(schema_id, evolved_yaml)
        result["evolved"] = True
        result["feature_summary"] = features_summary
        return result
    except Exception as e:
        logger.exception(f"Schema evolution for {schema_id} failed")
        return {"success": False, "evolved": False, "error": f"模式自动进化失败: {str(e)}"}
