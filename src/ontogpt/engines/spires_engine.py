"""
Main SPIRES Knowledge Extractor class.

This works by recursively constructing structured prompt-completions where
a pseudo-YAML structure is requested, where the YAML
structure corresponds to a template class.

Described in the SPIRES manuscript.
See https://arxiv.org/abs/2304.02711
"""

import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union, cast

import pydantic
import yaml
from linkml_runtime.linkml_model import ClassDefinition, ElementName, SlotDefinition
from oaklib import BasicOntologyInterface

from ontogpt.engines.knowledge_engine import (
    ANNOTATION_KEY_PROMPT,
    EXAMPLE,
    FIELD,
    OBJECT,
    KnowledgeEngine,
    chunk_text_by_char,
    chunk_text_by_sentence,
)
from ontogpt.io.utils import read_text_with_fallbacks
from ontogpt.io.yaml_wrapper import dump_minimal_yaml
from ontogpt.templates.core import ExtractionResult, NamedEntity
from ontogpt.utils.parse_utils import get_span_values, is_null_like_value, sanitize_text

this_path = Path(__file__).parent

CODE_FENCE = "```"

RESPONSE_ATOM = Any
RESPONSE_DICT = Dict[FIELD, Union[RESPONSE_ATOM, List[RESPONSE_ATOM]]]


@dataclass
class SPIRESEngine(KnowledgeEngine):
    """Knowledge extractor."""

    recurse: bool = True
    """If true, then complex non-named entity objects are always recursively parsed.
    If this is false AND the complex object is a pair, then token-based splitting is
    instead used.
    TODO: deprecate this, it's not clear that token-based splitting is better, due to
    the inability to control which tokens GPT will use"""

    sentences_per_window: Optional[int] = None
    """If set, this will split the text into chains of sentences,
    where this determines the maximum number of sentences per chain.
    The results are then merged together."""

    max_text_length: Optional[int] = None
    """If set, this will split the text into chunks based on this number of characters."""

    enable_neo4j_reuse: bool = True
    """If true, sub-extractions consult the Neo4j knowledge graph before calling the LLM."""

    @staticmethod
    def _as_object_dict(value: Union[pydantic.BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped
        raise TypeError(f"Cannot serialize object of type {type(value)}")

    @staticmethod
    def _merge_model_objects(
        current_object: pydantic.BaseModel, next_object: pydantic.BaseModel
    ) -> None:
        for field_name, value in next_object.model_dump().items():
            current_value = getattr(current_object, field_name, None)
            if isinstance(value, list):
                merged_list = list(current_value or [])
                for item in value:
                    if item not in merged_list:
                        merged_list.append(item)
                setattr(current_object, field_name, merged_list)
            elif value:
                setattr(current_object, field_name, value)

    def extract_from_text(
        self,
        text: str,
        cls: Optional[ClassDefinition] = None,
        object: OBJECT = None,
        show_prompt: bool = False,
    ) -> ExtractionResult:
        """
        Extract annotations from the given text.

        When validate_terms is set, the grounded identifiers of the finished
        result are validated against their ontologies and repaired once the
        outermost extraction (not the nested ones SPIRES runs for compound
        classes) has completed.

        :param text:
        :param cls:
        :param object: optional stub object
        :return:
        """
        self._extraction_depth += 1
        try:
            result = self._extract_from_text_unvalidated(
                text=text, cls=cls, object=object, show_prompt=show_prompt
            )
            if self._extraction_depth == 1 and self.validate_terms:
                self.validate_extraction_result(result)
        finally:
            self._extraction_depth -= 1
        return result

    def _extract_from_text_unvalidated(
        self,
        text: str,
        cls: Optional[ClassDefinition] = None,
        object: OBJECT = None,
        show_prompt: bool = False,
    ) -> ExtractionResult:
        self.extracted_named_entities = []  # Clear the named entity buffer
        self.in_flight_features = set()
        self._in_flight_lock = threading.Lock()
        # 实体级结果内存缓存，避免在同一个长文档中反复对相同实体重复发起 300 Token 小请求
        self._sub_extraction_cache: Dict[Tuple[str, str], RESPONSE_DICT] = {}
        self._sub_cache_lock = threading.Lock()

        # This indicates that the text will be chunked in some way
        have_chunks = False
        chunks: List[str] = []
        raw_text = ""

        logging.info("Cleaning text...")
        new_text = sanitize_text(text)

        # compare new_text to original text at byte-level
        try:
            b_orig = text.encode("utf-8")
            b_new = new_text.encode("utf-8")
        except Exception:
            # fallback to string-level compare if encoding fails
            if text != new_text:
                logging.info(
                    f"Text changed (string-level). original_len={len(text)} new_len={len(new_text)}"
                )
        else:
            if b_orig != b_new:
                minlen = min(len(b_orig), len(b_new))
                # find first differing byte index
                idx = next((i for i in range(minlen) if b_orig[i] != b_new[i]), None)
                if idx is None:
                    logging.info(
                        "Text byte-wise differs:"
                        f"original_len={len(b_orig)} new_len={len(b_new)}"
                        f"(identical up to {minlen} bytes)"
                    )
                else:
                    logging.info(
                        f"Text byte-wise differs at byte {idx}:"
                        f"original_len={len(b_orig)} new_len={len(b_new)}"
                    )
        text = new_text

        if self.sentences_per_window:
            chunks = list(chunk_text_by_sentence(text, self.sentences_per_window))
            have_chunks = True

        if self.max_text_length:
            chunks = list(chunk_text_by_char(text, self.max_text_length))
            have_chunks = True

        if have_chunks:
            extracted_object = None
            total_chunks = len(chunks)
            workers = getattr(self, "max_workers", 5) or 5

            if workers > 1 and total_chunks > 1:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                completed_count = 0

                def process_chunk(idx_and_chunk):
                    idx, chunk = idx_and_chunk
                    if getattr(self, "stop_requested", False):
                        raise InterruptedError("用户已手动停止任务")
                    r_text = self._raw_extract(chunk, cls=cls, object=object, show_prompt=show_prompt)
                    parsed_obj = self.parse_completion_payload(r_text, cls, object=object)
                    feats = getattr(parsed_obj, "auto_discovered_features", None) or []
                    if feats:
                        new_keys = []
                        for f in feats:
                            k = getattr(f, "key", "") or (f.get("key") if isinstance(f, dict) else "")
                            k = str(k).strip()
                            if k and len(k) < 30:
                                new_keys.append(k)
                        if new_keys and hasattr(self, "_in_flight_lock"):
                            with self._in_flight_lock:
                                self.in_flight_features.update(new_keys)
                    return idx, parsed_obj

                results_dict = {}
                with ThreadPoolExecutor(max_workers=min(workers, total_chunks)) as executor:
                    self._current_executor = executor
                    futures = [executor.submit(process_chunk, (i, ch)) for i, ch in enumerate(chunks, 1)]
                    try:
                        for future in as_completed(futures):
                            if getattr(self, "stop_requested", False):
                                executor.shutdown(wait=False, cancel_futures=True)
                                raise InterruptedError("用户已手动停止任务")
                            try:
                                idx, parsed_obj = future.result()
                            except InterruptedError:
                                executor.shutdown(wait=False, cancel_futures=True)
                                raise
                            results_dict[idx] = parsed_obj
                            completed_count += 1
                            cb = getattr(self, "progress_callback", None)
                            if cb:
                                try:
                                    pool_size = len(getattr(self, "in_flight_features", set()))
                                    feat_hint = ""
                                    if pool_size > 0:
                                        sample_k = list(getattr(self, "in_flight_features", set()))[:2]
                                        feat_hint = f" | ⚡进行中动态感知: [{', '.join(sample_k)}] (共{pool_size}项)"
                                    cb(completed_count, total_chunks, f"已并行完成 {completed_count}/{total_chunks} 个分块 (并发数: {workers}){feat_hint}")
                                except Exception:
                                    pass
                    finally:
                        self._current_executor = None

                # 按文档原始切块顺序依次合并
                for i in range(1, total_chunks + 1):
                    next_object = results_dict.get(i)
                    if next_object is None:
                        continue
                    if extracted_object is None:
                        extracted_object = next_object
                    else:
                        try:
                            self._merge_model_objects(extracted_object, next_object)
                        except AttributeError:
                            logging.error(f"Empty object: {next_object}")
            else:
                for idx, chunk in enumerate(chunks, 1):
                    if getattr(self, "stop_requested", False):
                        logging.info("Extraction aborted by user stop request.")
                        raise InterruptedError("用户已手动停止任务")

                    cb = getattr(self, "progress_callback", None)
                    if cb:
                        try:
                            cb(idx, total_chunks, f"正在处理第 {idx}/{total_chunks} 个文档分块...")
                        except Exception:
                            pass

                    raw_text = self._raw_extract(chunk, cls=cls, object=object, show_prompt=show_prompt)
                    logging.info(f"RAW TEXT: {raw_text}")
                    next_object = self.parse_completion_payload(
                        raw_text, cls, object=object  # type: ignore
                    )
                    feats = getattr(next_object, "auto_discovered_features", None) or []
                    if feats:
                        new_keys = []
                        for f in feats:
                            k = getattr(f, "key", "") or (f.get("key") if isinstance(f, dict) else "")
                            k = str(k).strip()
                            if k and len(k) < 30:
                                new_keys.append(k)
                        if new_keys:
                            self.in_flight_features.update(new_keys)

                    pool_size = len(getattr(self, "in_flight_features", set()))
                    feat_hint = ""
                    if pool_size > 0:
                        sample_k = list(getattr(self, "in_flight_features", set()))[:2]
                        feat_hint = f" | ⚡进行中动态感知: [{', '.join(sample_k)}] (共{pool_size}项)"
                    if cb:
                        try:
                            cb(idx, total_chunks, f"已完成第 {idx}/{total_chunks} 个文档分块{feat_hint}")
                        except Exception:
                            pass
                    if extracted_object is None:
                        extracted_object = next_object
                    else:
                        try:
                            self._merge_model_objects(extracted_object, next_object)
                        except AttributeError:
                            logging.error(f"Empty object: {next_object}")
        else:
            if getattr(self, "stop_requested", False):
                logging.info("Extraction aborted by user stop request.")
                raise InterruptedError("用户已手动停止任务")

            cb = getattr(self, "progress_callback", None)
            if cb:
                try:
                    cb(1, 1, "正在调用大模型进行实体与本体关系抽取...")
                except Exception:
                    pass

            raw_text = self._raw_extract(text=text, cls=cls, object=object, show_prompt=show_prompt)
            logging.info(f"RAW TEXT: {raw_text}")
            extracted_object = self.parse_completion_payload(
                raw_text, cls, object=object  # type: ignore
            )

        # Add spans to entities
        self.extracted_named_entities = self.get_spans(
            input_text=text, named_entities=self.extracted_named_entities
        )

        return ExtractionResult(
            input_id=None,
            input_title=None,
            input_text=text,
            raw_completion_output=raw_text,
            prompt=self.last_prompt,
            extracted_object=extracted_object,
            named_entities=self.extracted_named_entities,
            # Note these are the named entities from the last extraction,
            # not the full list of all named entities across all extractions
        )

    def _safe_induced_slot(
        self, slot_name: str, class_name: str
    ) -> Optional[SlotDefinition]:
        """Safely fetch an induced slot without letting LinkML raise ValueError."""
        sv = self._require_schemaview()
        try:
            if slot_name in sv.class_slots(class_name):
                return sv.induced_slot(slot_name, class_name)
            return sv.induced_slot(slot_name, class_name)
        except Exception:
            return None

    def _extract_from_text_to_dict(
        self, text: str, cls: Optional[ClassDefinition] = None
    ) -> RESPONSE_DICT:
        # Placeholder values such as "none" or "N/A" are not real text to split
        # into fields. Recursing on them wastes an LLM call and, because the model
        # has nothing to extract, it often replies with a clarifying question that
        # the parser then rejects ("does not contain a colon; ignoring").
        if is_null_like_value(text):
            logging.info(f"Skipping sub-extraction for null-like text: {text!r}")
            return {}

        clean_text = text.strip()
        cls_name = cls.name if cls else ""
        cache_key = (clean_text, cls_name)

        # 1. 检查内存缓存 (单次任务去重)
        if hasattr(self, "_sub_extraction_cache") and hasattr(self, "_sub_cache_lock"):
            with self._sub_cache_lock:
                if cache_key in self._sub_extraction_cache:
                    logging.debug(f"Sub-extraction memory cache hit for: {clean_text}")
                    return dict(self._sub_extraction_cache[cache_key])

        # 2. 检查 Neo4j 知识图谱已沉淀知识 (跨任务/全域图谱知识复用)
        if getattr(self, "enable_neo4j_reuse", True):
            try:
                from ontogpt.clients.neo4j_service import neo4j_service
                neo_hit = neo4j_service.lookup_entity(clean_text, cls_name)
                if neo_hit:
                    logging.info(f"✨ [Neo4j Graph-in-the-Loop] Successfully reused known entity: {clean_text} ({cls_name}), skipping LLM call!")
                    if hasattr(self, "_sub_extraction_cache") and hasattr(self, "_sub_cache_lock"):
                        with self._sub_cache_lock:
                            self._sub_extraction_cache[cache_key] = neo_hit
                    return dict(neo_hit)
            except Exception as e:
                logging.debug(f"Neo4j lookup hook skipped: {e}")

        raw_text = self._raw_extract(text=text, cls=cls)
        parsed = self._parse_response_to_dict(raw_text, cls)

        # 写入缓存
        if hasattr(self, "_sub_extraction_cache") and hasattr(self, "_sub_cache_lock"):
            with self._sub_cache_lock:
                self._sub_extraction_cache[cache_key] = parsed

        return parsed

    def generate_and_extract(
        self, entity: str, prompt_template: str = "", show_prompt: bool = False, **kwargs
    ) -> ExtractionResult:
        """
        Generate a description using an LLM and then extract from it using SPIRES.

        :param entity:
        :param kwargs:
        :return:
        """
        if prompt_template == "":
            prompt_template = "Generate a comprehensive description of {entity}.\n"
        prompt = prompt_template.format(entity=entity)
        if self.client is not None:
            payload = self.client.complete(prompt=prompt, show_prompt=show_prompt)
        else:
            payload = ""
        return self.extract_from_text(payload, **kwargs)

    def iteratively_generate_and_extract(
        self,
        entity: str,
        cache_path: Union[str, Path],
        iteration_slots: List[str],
        adapter: Optional[BasicOntologyInterface] = None,
        clear=False,
        max_iterations=10,
        prompt_template=None,
        show_prompt: bool = False,
        **kwargs,
    ) -> Iterator[ExtractionResult]:
        def _remove_parenthetical_context(s: str):
            return re.sub(r"\(.*\)", "", s)

        iteration = 0
        if isinstance(cache_path, str):
            cache_path = Path(cache_path)
        db: Dict[str, Any] = {"processed_entities": [], "entities_in_queue": [], "results": []}
        if cache_path:
            if cache_path.exists() and not clear:
                loaded_db = yaml.safe_load(read_text_with_fallbacks(cache_path))
                if isinstance(loaded_db, dict):
                    db = loaded_db
                if "entities_in_queue" not in db:
                    db["entities_in_queue"] = []
        if entity not in db["processed_entities"]:
            db["entities_in_queue"].append(entity)
        if prompt_template is None:
            prompt_template = (
                "Generate a comprehensive description of {entity}. "
                + "The description should include the information on"
                + " and ".join(iteration_slots)
                + ".\n"
            )
        while db["entities_in_queue"] and iteration < max_iterations:
            iteration += 1
            next_entity = db["entities_in_queue"].pop(0)
            logging.info(f"ITERATION {iteration}, entity={next_entity}")
            # check if entity matches a curie pattern using re
            if re.match(r"^[A-Z]+:[A-Z0-9]+$", next_entity):
                curie = next_entity
                if adapter is not None:
                    next_entity = adapter.label(next_entity) or next_entity
            else:
                curie = None
            result = self.generate_and_extract(
                next_entity, prompt_template=prompt_template, show_prompt=show_prompt, **kwargs
            )
            if curie:
                if result.extracted_object:
                    result.extracted_object.id = curie
            db["results"].append(result)
            db["processed_entities"].append(next_entity)
            yield result
            for s in iteration_slots:
                # if s not in result.extracted_object:
                #    raise ValueError(f"Slot {s} not found in {result.extracted_object}")
                vals = getattr(result.extracted_object, s, [])
                if not vals:
                    logging.info("dead-end: no values found for slot")
                    continue
                if not isinstance(vals, list):
                    vals = [vals]
                for val in vals:
                    entity = val
                    if result.named_entities is not None:
                        for ne in result.named_entities:
                            if ne.id == val:
                                entity = ne.label
                                if ne.id.startswith("AUTO"):
                                    # Sometimes the value of some slots will lack
                                    context = next_entity
                                    context = re.sub(r"\(.*\)", "", context)
                                    entity = f"{entity} ({context})"
                                else:
                                    entity = ne.id
                                break
                    queue_deparenthesized = [
                        _remove_parenthetical_context(e) for e in db["entities_in_queue"]
                    ]
                    if (
                        entity not in db["processed_entities"]
                        and entity not in db["entities_in_queue"]
                        and _remove_parenthetical_context(entity) not in queue_deparenthesized
                    ):
                        db["entities_in_queue"].append(entity)
            with open(cache_path, "w", encoding="utf-8") as f:
                # TODO: consider a more robust backend e.g. mongo
                f.write(dump_minimal_yaml(db))

    def generalize(
        self,
        object: Union[pydantic.BaseModel, dict],
        examples: List[EXAMPLE],
        show_prompt: bool = False,
    ) -> pydantic.BaseModel:
        """
        Generalize the given examples.

        :param object:
        :param examples:
        :return:
        """
        cls = self._require_template_class()
        sv = self._require_schemaview()
        prompt = "example:\n"
        for example in examples:
            prompt += f"{self.serialize_object(example)}\n\n"
        prompt += "\n\n===\n\n"
        object = self._as_object_dict(object)
        for k, v in object.items():
            if v:
                slot = self._safe_induced_slot(k, cls.name)
                if slot is None:
                    continue
                prompt += f"{k}: {self._serialize_value(v, slot)}\n"
        logging.debug(f"PROMPT: {prompt}")
        payload = self._require_client().complete(prompt, show_prompt=show_prompt)
        prediction = self.parse_completion_payload(payload, object=object)
        return prediction

    def map_terms(
        self, terms: List[str], ontology: str, show_prompt: bool = False
    ) -> Dict[str, str]:
        """
        Map the given terms to the given ontology.

        :param terms:
        :param ontology:
        :return:
        """
        # TODO: make a separate config
        examples = {
            "go": {
                "nucleui": "nucleus",
                "mitochondrial": "mitochondrion",
                "signaling": "signaling pathway",
                "cysteine biosynthesis": "cysteine biosynthetic process",
                "alcohol dehydrogenase": "alcohol dehydrogenase activity",
            },
            "uberon": {
                "feet": "pes",
                "forelimb, left": "left forelimb",
                "hippocampus": "Ammons horn",
            },
        }
        ontology = ontology.lower()
        if ontology in examples:
            example = examples[ontology]
        else:
            example = examples["uberon"]
        prompt = "Normalize the following semicolon separated\
            list of terms to the {ontology.upper()} ontology\n\n"
        prompt += "For example:\n\n"
        for k, v in example.items():
            prompt += f"{k}: {v}\n"
        prompt += "===\n\nTerms:"
        prompt += "; ".join(terms)
        prompt += "===\n\n"
        payload = self._require_client().complete(prompt, show_prompt=show_prompt)
        # outer parse
        best_results: List[str] = []
        for sep in ["\n", "; "]:
            results = payload.split(sep)
            if len(results) > len(best_results):
                best_results = results

        def normalize(s: str) -> str:
            s = s.strip()
            s.replace("_", " ")
            return s.lower()

        mappings = {}
        for result in best_results:
            if ":" not in result:
                logging.error(f"Count not parse result: {result}")
                continue
            k, v = result.strip().split(":", 1)
            k = k.strip()
            v = v.strip()
            for t in terms:
                if normalize(t) == normalize(k):
                    mappings[t] = v
                    break
        for t in terms:
            if t not in mappings:
                logging.warning(f"Could not map term: {t}")
        return mappings

    def serialize_object(self, example: EXAMPLE, cls: Optional[ClassDefinition] = None) -> str:
        template_cls = self._require_template_class(cls)
        class_name = template_cls.name
        if isinstance(example, str):
            return example
        example = self._as_object_dict(example)
        lines = []
        sv = self._require_schemaview()
        for k, v in example.items():
            if not v:
                continue
            slot = self._safe_induced_slot(k, class_name)
            if slot is None:
                continue
            v_serialized = self._serialize_value(v, slot)
            lines.append(f"{k}: {v_serialized}")
        return "\n".join(lines)

    def _serialize_value(self, val: Any, slot: SlotDefinition) -> str:
        if val is None:
            return ""
        if isinstance(val, list):
            return "; ".join([self._serialize_value(v, slot) for v in val if v])
        if isinstance(val, dict):
            return " - ".join([self._serialize_value(v, slot) for v in val.values() if v])
        sv = self._require_schemaview()
        if slot.range in sv.all_classes():
            range_cls = sv.get_class(slot.range)
            if self.labelers:
                labelers = list(self.labelers)
            else:
                labelers = []
            if range_cls is not None:
                labelers += self.get_annotators(range_cls)
            if labelers:
                for labeler in labelers:
                    label = labeler.label(val)
                    if label:
                        return label
        return val

    def _raw_extract(
        self,
        text: str,
        cls: Optional[ClassDefinition] = None,
        object: OBJECT = None,
        show_prompt: bool = False,
    ) -> str:
        """
        Extract annotations from the given text.

        :param text:
        :return:
        """
        prompt = self.get_completion_prompt(cls=cls, text=text, object=object)
        self.last_prompt = prompt
        payload = self._require_client().complete(prompt=prompt, show_prompt=show_prompt)
        return payload

    def get_completion_prompt(
        self, cls: Optional[ClassDefinition] = None, text: str = "", object: OBJECT = None
    ) -> str:
        """Get the prompt for the given template."""
        template_cls = self._require_template_class(cls)
        class_name = template_cls.name
        sv = self._require_schemaview()
        if not text or ("\n" in text or len(text) > 60):
            prompt = (
                "From the text below, extract the following entities in the following format:\n\n"
            )
        else:
            prompt = "Split the following piece of text into fields in the following format:\n\n"
        for slot in sv.class_induced_slots(class_name):
            if self.slot_is_skipped(slot):
                continue
            annotation_prompt = self._annotation_value(slot.annotations, ANNOTATION_KEY_PROMPT)
            if annotation_prompt is not None:
                slot_prompt = annotation_prompt
            elif slot.description:
                slot_prompt = slot.description
            else:
                if slot.multivalued:
                    slot_prompt = f"semicolon-separated list of {slot.name}s"
                else:
                    slot_prompt = f"the value for {slot.name}"
            if slot.range in sv.all_enums():
                enum_def = sv.get_enum(slot.range)
                if enum_def is not None:
                    pvs = [str(k) for k in enum_def.permissible_values.keys()]
                    slot_prompt += f"Must be one of: {', '.join(pvs)}"
            if slot.name == "auto_discovered_features":
                in_flight_pool = getattr(self, "in_flight_features", None)
                if in_flight_pool:
                    sample_keys = list(in_flight_pool)[:12]
                    slot_prompt += f" (进行中文档已动态捕获专有参数: {', '.join(sample_keys)}，后文遇到请重点对齐提取，并继续发掘其他新指标)"
            prompt += f"{slot.name}: <{slot_prompt}>\n"
        prompt += (
            "\nExtraction Rules:\n"
            "- Only extract facts explicitly stated in the text.\n"
            "- DO NOT invent values. If an attribute is not present, DO NOT write '未明确指定', 'null', 'None', or 'N/A'; simply omit that line.\n"
            "- Strictly output one slot per line ('slot_name: value'). Never concatenate multiple sub-slots into a single line.\n"
        )
        prompt = f"{prompt}\n\nText:\n{text}\n\n===\n\n"
        if object:
            if isinstance(object, str):
                logging.error(
                    f"Error in getting prompt. Cannot serialize object of type {type(object)}"
                )
                raise ValueError(
                    f"Error in getting prompt. Cannot serialize object of type {type(object)}"
                )
            object_dict = self._as_object_dict(object)
            for k, v in object_dict.items():
                if v:
                    slot = self._safe_induced_slot(k, class_name)
                    if slot is None:
                        continue
                    prompt += f"{k}: {self._serialize_value(v, slot)}\n"
        return prompt

    def _parse_response_to_dict(
        self, results: str, cls: Optional[ClassDefinition] = None
    ) -> RESPONSE_DICT:
        """
        Parse the pseudo-YAML response from OpenAI into a dictionary object.

        E.g.

            foo: a; b; c

        becomes

            {"foo": ["a", "b", "c"]}

        The response may already be in markdown and/or JSON,
        in which case we need to recognize the format.
        JSON may be parsed as-is but may be malformed or over-processed
        as compared to our template (e.g., it may separate key-value pairs
        where we expect them to be concatenated)

        :param results:
        :return:
        """
        promptable_slots = self.promptable_slots(cls)
        is_json = False

        # First remove any code fences
        # and any adjacent strings on the same line
        results = re.sub(r"```[^`\n]*", "", results, flags=re.DOTALL)

        # Try to parse as JSON
        # The JSON may still be malformed.
        # If so, it's not JSON and we need to parse it as YAML-like
        # So just to be sure we remove the JSON delimiters in that case
        ann: RESPONSE_DICT = {}
        raw_ann: object = None
        try:
            raw_ann = json.loads(results)
            is_json = True
        except json.decoder.JSONDecodeError:
            for ch in ["{", "}", '"']:
                results = results.replace(ch, "")

        if is_json:
            if not isinstance(raw_ann, dict):
                return ann
            for entry, raw_value in raw_ann.items():
                if isinstance(raw_value, list):
                    values = "; ".join(str(v) for v in raw_value)
                elif isinstance(raw_value, dict):
                    values = "; ".join([f"{k} - {v}" for k, v in raw_value.items()])
                else:
                    values = str(raw_value)
                line = f"{entry}: {values}"
                r = self._parse_line_to_dict(line, cls)
                if r is not None:
                    field, val = r
                    ann[field] = val
        else:
            # First split the text into sections, denoted by presence of multiple newlines
            # Each section may still have multiple fields, but we don't know how
            # they will be formatted
            sections = results.replace("*", "").split("\n\n")
            for section in sections:
                lines = section.splitlines()
                continued_line = ""
                for line in lines:
                    line = line.replace("*", "").strip()
                    line = line.replace("：", ": ")

                    # If previous line was marked continued, but current line is a new key-value field (contains ':'),
                    # finish the previous line immediately instead of gluing them together!
                    if len(continued_line) > 0 and ":" in line:
                        r = self._parse_line_to_dict(continued_line, cls)
                        if r is not None:
                            field, val = r
                            ann[field] = val
                        continued_line = ""

                    # The line may be split into multiple lines if it ends in ';' AND doesn't start with a new field
                    if line.endswith(";"):
                        # If line itself is a complete key-value pair, parse it directly rather than blindly continuing
                        if ":" in line:
                            line_to_parse = line.rstrip(";")
                            r = self._parse_line_to_dict(line_to_parse, cls)
                            if r is not None:
                                field, val = r
                                ann[field] = val
                            continued_line = ""
                            continue
                        else:
                            logging.info(
                                f"This line ends in a delimiter, assuming continuation: {line}"
                            )
                            continued_line = line
                            continue

                    if ":" in line and not line.split(":", 1)[1].strip():
                        logging.info(f"This line looks empty, assuming continuation: {line}")
                        if len(continued_line) > 0:
                            logging.info(f"Finishing previous continued line: {continued_line}")
                            r = self._parse_line_to_dict(continued_line, cls)
                            if r is not None:
                                field, val = r
                                ann[field] = val
                        continued_line = line
                        continue
                    # We may be continuing a numeric list
                    if (line.split("."))[0].isdigit():
                        logging.info(
                            f"Line '{line}' is a numeric item; continuing from {continued_line}"
                        )
                        # Remove the leading numeral from the line
                        line = line.split(".", 1)[1].strip()
                        continued_line = continued_line + line + ";"
                        continue
                    if not line:
                        continue
                    if line.startswith(CODE_FENCE):
                        continue
                    if ":" not in line:
                        if len(promptable_slots) == 1:
                            slot = promptable_slots[0]
                            logging.info(
                                f"Coercing to YAML-like with key {slot.name}: Original line: {line}"
                            )
                            line = f"{slot.name}: {line}"
                        elif len(continued_line) > 0:
                            logging.info(f"Line '{line}' continuing from {continued_line}")
                            line = continued_line + ";" + line
                        if ":" not in line:
                            # Recoverable: the model returned a line we can't map
                            # to a field (often a clarification/refusal during a
                            # recursive sub-extraction). We skip it and continue.
                            logging.warning(f"Line '{line}' does not contain a colon; ignoring")
                            continue
                    else:
                        # We made it this far but may still have a continued line
                        # So parse that first
                        if len(continued_line) > 0:
                            line = continued_line
                    r = self._parse_line_to_dict(line, cls)
                    continued_line = ""
                    if r is not None:
                        field, val = r
                        ann[field] = val
                if len(continued_line) > 0:
                    logging.info(f"Finishing continued line: {continued_line}")
                    r = self._parse_line_to_dict(continued_line, cls)
                    if r is not None:
                        field, val = r
                        ann[field] = val
        return ann

    def _parse_line_to_dict(
        self, line: str, cls: Optional[ClassDefinition] = None
    ) -> Optional[Tuple[FIELD, RESPONSE_ATOM]]:
        template_cls = self._require_template_class(cls)
        class_name = template_cls.name
        sv = self._require_schemaview()
        # each line is a key-value pair, with key as field
        # and value as val. An error gets raised if the value is empty
        logging.info(f"PARSING LINE: {line}")
        try:
            field, val = line.split(":", 1)
        except ValueError:
            field = line.split(":", 1)[0]
            val = ""

        # 立即去除首尾空格，若只有空白字符（如 "bay_name: "），直接判定为空值
        field = field.strip()
        val = val.strip()

        # 智能过滤空值与占位词（如 "未明确指定", "null", "N/A"），避免无意义数据污染图谱
        from ontogpt.utils.parse_utils import is_null_like_value
        if is_null_like_value(val):
            return None

        # Field normalization:
        # The LLM may mutate the output format somewhat,
        # randomly pluralizing or replacing spaces with underscores
        field = field.lower().replace(" ", "_")
        logging.debug(f"  FIELD: {field}")

        # Filter out common conversational/chatter lines emitted by conversational LLMs
        conversational_prefixes = (
            "based_on",
            "here_is",
            "here_are",
            "(note",
            "note",
            "please_note",
            "as_requested",
            "sure",
            "according_to",
            "extraction_result",
            "summary",
        )
        if any(field.startswith(p) for p in conversational_prefixes) or field == "slot_name":
            logging.debug(f"Filtered conversational boilerplate line: {line}")
            return None

        cls_slots = sv.class_slots(class_name)
        slot = None
        if field in cls_slots:
            slot = sv.induced_slot(field, class_name)
        else:
            # Try removing pluralization or singular-to-plural
            if field.endswith("s") and field[:-1] in cls_slots:
                slot = sv.induced_slot(field[:-1], class_name)
            elif (field + "s") in cls_slots:
                slot = sv.induced_slot(field + "s", class_name)
            elif field.endswith("_feature") and (field + "s") in cls_slots:
                slot = sv.induced_slot(field + "s", class_name)

        # Fallback slot alias matching for common variations emitted by LLMs
        if not slot:
            aliases = {
                # 错别字与拼写容错（如 maintenace_actions 缺 n）
                "maintenace_actions": "maintenance_actions",
                "maintenace": "maintenance_actions",
                "dispatch_actions": "dispatch_and_switching_ops",
                # 电力与设备类别名
                "fault_type": "fault_incident",
                "fault": "fault_incident",
                "fault_event": "fault_incident",
                "fault_detail": "fault_incident",
                "dga_indicator": "measurements_and_indicators",
                "insulation_parameter": "measurements_and_indicators",
                "measurement": "measurements_and_indicators",
                "measurements": "measurements_and_indicators",
                "indicator": "measurements_and_indicators",
                "indicators": "measurements_and_indicators",
                "electrical_measurement": "measurements_and_indicators",
                "auto_discovered_feature": "auto_discovered_features",
                "custom_feature": "auto_discovered_features",
                "features": "auto_discovered_features",
                "characteristic": "auto_discovered_features",
                "characteristics": "auto_discovered_features",
                "substation": "location",
                "plant": "location",
                "line": "location",
                "equipment": "primary_equipment",
                "equipments": "primary_equipment",
                "primary": "primary_equipment",
                "transformer": "primary_equipment",
                "main_transformer": "primary_equipment",
                "breaker": "primary_equipment",
                "circuit_breaker": "primary_equipment",
                "bushing": "primary_equipment",
                "switch": "primary_equipment",
                "secondary": "secondary_system",
                "secondary_devices": "secondary_system",
                "protection": "relay_protection_actions",
                "protection_scheme": "relay_protection_actions",
                "protection_action": "relay_protection_actions",
                "relay_protection": "relay_protection_actions",
                "dispatch": "dispatch_and_switching_ops",
                "switching": "dispatch_and_switching_ops",
                "switching_operations": "dispatch_and_switching_ops",
                "dispatch_actions": "dispatch_and_switching_ops",
                "maintenance": "maintenance_actions",
                "maintenance_action": "maintenance_actions",
                "maintenance_measures": "maintenance_actions",
                "repair": "maintenance_actions",
                # 通用模板别名（医疗/生物/菜谱等通用别名）
                "title": "event_title",
                "name": "event_title" if "event_title" in cls_slots else ("label" if "label" in cls_slots else None),
                "time": "occurrence_time",
                "date": "occurrence_time",
                "disease": "subject" if "subject" in cls_slots else None,
                "drug": "subject" if "subject" in cls_slots else None,
                "gene": "subject" if "subject" in cls_slots else None,
            }
            mapped_field = aliases.get(field)
            if mapped_field and mapped_field in cls_slots:
                slot = sv.induced_slot(mapped_field, class_name)

        # 智能子字符串与前缀模糊自适应（如 LLM 输出 primary_equipments 或 fault_incident_details）
        if not slot:
            clean_f = field.replace("-", "_")
            for cs in cls_slots:
                if clean_f == cs or clean_f.startswith(cs) or cs.startswith(clean_f):
                    slot = sv.induced_slot(cs, class_name)
                    break

        if not val:
            # 如果是主键/唯一标识符 id，但在输出中为空（如 "id: "），由系统自动生成 UUID 填充，禁止抛错！
            if slot and slot.identifier:
                auto_id = str(uuid.uuid4())
                auto_prefix = getattr(self, "auto_prefix", "AUTO")
                if slot.range in ["uriorcurie", "uri"]:
                    return slot.name, f"{auto_prefix}:{auto_id}"
                return slot.name, auto_id

            # 允许非必填字段为空值静默跳过，避免爆出 Expected 1 value but got []
            if slot and slot.required:
                logging.debug(f"Required slot {slot.name} is empty in model response; generating default.")
                return None
            return None

        # 智能语义推断与自适应分流（Semantic Auto-Classification）：
        # 如果大模型输出了 Schema 预置槽位之外的新概念/新字段（如 "汽轮机型式"、"调压方式"、"接线组别"、"控制逻辑"），
        # 绝不硬丢弃，而是分析其工程语境，合理地自动挂载到正确的目标类别中（设备/保护动作/量测/动态特征）：
        if not slot and val.strip():
            combined = f"{field} {val}".lower()
            # 1. 设备与型式类 -> 归入 primary_equipment
            if any(k in combined for k in ["型式", "机型", "设备", "机组", "汽轮机", "锅炉", "压缩机", "电机", "变压器", "水泵", "断路器", "转子", "叶轮", "蓄电池", "轴承", "除水器", "滤芯", "膜"]):
                if "primary_equipment" in cls_slots:
                    slot = sv.induced_slot("primary_equipment", class_name)
                    field = "primary_equipment"
                    vals = [{"name": field if field != "primary_equipment" else line.split(":", 1)[0].strip(), "equipment_category": "动力与电气设备", "component_involved": val.strip()}]
                    return field, vals
            # 2. 继电保护与控制逻辑类 -> 归入 relay_protection_actions
            elif any(k in combined for k in ["逻辑", "联锁", "保护", "投入条件", "控制", "调节", "偏置", "切换", "闭锁", "速断", "定值", "次序", "voting", "voting"]):
                if "relay_protection_actions" in cls_slots:
                    slot = sv.induced_slot("relay_protection_actions", class_name)
                    field = "relay_protection_actions"
                    vals = [{"protection_name": line.split(":", 1)[0].strip(), "trip_breaker": None, "reclose_result": val.strip()}]
                    return field, vals
            # 3. 测量数据、材质材料、技术指标 -> 归入 measurements_and_indicators
            elif any(k in combined for k in ["材质", "材料", "容积", "重量", "压力", "电流", "电压", "等级", "组别", "方式", "温度", "精度", "比例", "水质", "成分", "率", "ip", "scph", "scm", "scs"]):
                if "measurements_and_indicators" in cls_slots:
                    slot = sv.induced_slot("measurements_and_indicators", class_name)
                    field = "measurements_and_indicators"
                    vals = [{"parameter_name": line.split(":", 1)[0].strip(), "value_with_unit": val.strip()}]
                    return field, vals
            # 4. 其他未知扩展特性 -> 兜底归入 auto_discovered_features
            elif "auto_discovered_features" in cls_slots:
                slot = sv.induced_slot("auto_discovered_features", class_name)
                val = f"{field} - {val}"
                field = "auto_discovered_features"

        if not slot:
            return None

        inlined = slot.inlined
        slot_range = sv.get_class(slot.range)
        if not inlined:
            if slot.range in sv.all_classes() and slot_range is not None:
                inlined = sv.get_identifier_slot(slot_range.name) is None
        val = val.strip()
        if slot.multivalued:
            vals = [v.strip() for v in val.replace("；", ";").split(";")]
        else:
            vals = [val]
        vals = [val for val in vals if val]
        logging.debug(f"SLOT: {slot.name} INL: {inlined} VALS: {vals}")
        if inlined:
            if slot_range is None:
                logging.warning(f"Cannot determine inlined range for {slot.name}")
                return None
            transformed = False
            slots_of_range = sv.class_slots(slot_range.name)
            # 对于二元键值对（如 KeyValuePair: key, value），进行全场景智能解构：
            # 兼容 "键 - 值"、"键: 值"、"键 空格 值" 以及单值短语（自动以短语为键，值记为"是/存在/已配置"）
            direct_split_done = False
            if len(slots_of_range) == 2:
                parsed_pairs = []
                for v in vals:
                    # 严格使用安全的键值分隔符，绝不能在 "/" 或孤立 "-" 盲目拆分（避免破坏 DL/T 1717、15s/12s 等技术代号与复合单位）
                    split_item = None
                    for sep in [" - ", "： ", "：", ": "]:
                        if sep in v:
                            parts = v.split(sep, 1)
                            split_item = {slots_of_range[0]: parts[0].strip(), slots_of_range[1]: parts[1].strip()}
                            break
                    # 若无显式连字符，尝试空格分隔（如 "材料 SCM440 (轴)"）
                    if not split_item and " " in v.strip():
                        parts = v.strip().split(None, 1)
                        if len(parts) == 2 and not parts[0].endswith(("/", "-", "T")):
                            split_item = {slots_of_range[0]: parts[0].strip(), slots_of_range[1]: parts[1].strip()}
                    if not split_item:
                        split_item = {slots_of_range[0]: v.strip(), slots_of_range[1]: "存在"}

                    if split_item and not is_null_like_value(split_item[slots_of_range[0]]):
                        parsed_pairs.append(split_item)

                vals = parsed_pairs
                direct_split_done = True

            if not direct_split_done:
                if self.recurse or len(slots_of_range) > 2:
                    if getattr(self, "stop_requested", False):
                        raise InterruptedError("用户已手动停止任务")
                    logging.debug(f"  RECURSING ON SLOT: {slot.name}, range={slot_range.name}")

                    # 高并发提速：若子实体列表 > 1，采用轻量级线程池并行发起子抽取，大幅缩减串行 RTT 延迟
                    if len(vals) > 1:
                        from concurrent.futures import ThreadPoolExecutor

                        sub_workers = min(len(vals), 10)
                        ordered_vals = [None] * len(vals)

                        def _do_sub_extract(index_and_v):
                            idx, sub_v = index_and_v
                            if getattr(self, "stop_requested", False):
                                return idx, {}
                            res = self._extract_from_text_to_dict(sub_v, slot_range)
                            return idx, res

                        with ThreadPoolExecutor(max_workers=sub_workers) as sub_exec:
                            for idx, res in sub_exec.map(_do_sub_extract, enumerate(vals)):
                                ordered_vals[idx] = res

                        vals = [v for v in ordered_vals if v]
                    else:
                        vals = [
                            self._extract_from_text_to_dict(v, slot_range) for v in vals  # type: ignore
                        ]
                    # Drop empty sub-extractions (e.g. from null-like placeholder values)
                    # so we don't emit empty inlined objects.
                    vals = [v for v in vals if v]
                    if not vals:
                        return None
                else:
                    for sep in [" - ", "：", ":", "/", "*", "-"]:
                        if all([sep in v for v in vals]):
                            vals = [
                                dict(zip(slots_of_range, v.split(sep, 1))) for v in vals  # type: ignore
                            ]
                            for v in vals:
                                for k in v.keys():  # type: ignore
                                    v[k] = v[k].strip()  # type: ignore
                            transformed = True
                            break
                    if not transformed:
                        logging.warning(f"Did not find separator in {vals} for line {line}")
                        return None
        # transform back from list to single value if not multivalued
        if slot.multivalued:
            final_val = vals
        else:
            if not vals:
                # 单值槽位为空列表时静默返回 None，避免抛出 Expected 1 value 错误
                return None
            final_val = vals[0]  # type: ignore
        # 必须返回规范化槽位名 slot.name，确保后续实例化字典 key 与 LinkML Schema 100% 一致！
        return slot.name, final_val

    def parse_completion_payload(
        self,
        results: str,
        cls: Optional[ClassDefinition] = None,
        object: Optional[Dict[str, Any]] = None,
    ) -> pydantic.BaseModel:
        """
        Parse the completion payload into a pydantic class.

        :param results:
        :param cls:
        :param object: stub object
        :return:
        """
        raw = self._parse_response_to_dict(results, cls)
        logging.debug(f"RAW: {raw}")
        if object:
            raw = {**object, **raw}
        self._auto_add_ids(raw, cls)
        grounded = self.ground_annotation_object(raw, cls)
        if grounded is None:
            raise ValueError("Could not ground completion payload")
        return grounded

    def _auto_add_ids(self, ann: RESPONSE_DICT, cls: Optional[ClassDefinition] = None) -> None:
        template_cls = self._require_template_class(cls)
        class_name = template_cls.name
        sv = self._require_schemaview()
        for slot in sv.class_induced_slots(class_name):
            if slot.identifier:
                if slot.name not in ann:
                    auto_id = str(uuid.uuid4())
                    auto_prefix = self.auto_prefix
                    if slot.range == "uriorcurie" or slot.range == "uri":
                        ann[slot.name] = f"{auto_prefix}:{auto_id}"
                    else:
                        ann[slot.name] = auto_id

    def ground_annotation_object(
        self, ann: Optional[RESPONSE_DICT], cls: Optional[ClassDefinition] = None
    ) -> Optional[pydantic.BaseModel]:
        """Ground the direct parse of the OpenAI payload.

        The raw openAI payload is a YAML-like string, which is parsed to
        a response dictionary.

        This dictionary is then grounded, using this method

        :param ann: Raw annotation object
        :param cls: schema class the ground object should instantiate
        :return: Grounded annotation object
        """
        logging.debug(f"Grounding annotation object {ann}")
        template_cls = self._require_template_class(cls)
        class_name = template_cls.name
        sv = self._require_schemaview()
        new_ann: Dict[str, Any] = {}
        if ann is None:
            logging.error(f"Cannot ground None annotation, cls={class_name}")
            return None
        cls_slots = sv.class_slots(class_name)
        for field, vals in list(ann.items()):
            slot = None
            if field in cls_slots:
                slot = self._safe_induced_slot(field, class_name)
            else:
                # 容错别名或拼写错误字典
                alias_map = {
                    "maintenace_actions": "maintenance_actions",
                    "maintenace": "maintenance_actions",
                    "fault_type": "fault_incident",
                    "equipment": "primary_equipment",
                    "equipments": "primary_equipment",
                    "primary": "primary_equipment",
                    "measurement": "measurements_and_indicators",
                    "measurements": "measurements_and_indicators",
                    "indicator": "measurements_and_indicators",
                    "indicators": "measurements_and_indicators",
                }
                mapped = alias_map.get(field)
                if mapped and mapped in cls_slots:
                    slot = self._safe_induced_slot(mapped, class_name)
                    if slot:
                        field = mapped
                if not slot:
                    slot = self._safe_induced_slot(field, class_name)

            if slot is None:
                logging.debug(f"Cannot find slot {field} in {class_name}; safe skip.")
                continue

            # 核心防御：必须以 Schema 定义的 slot.multivalued 为准，而不是以入参是不是 list 为准！
            # 否则当大模型把单值字符串字段输出为空列表 [] 时，原版会错判为 multivalued=True 并生成 []，引发 Pydantic 校验崩溃！
            multivalued = bool(slot.multivalued)
            if isinstance(vals, list):
                if not multivalued:
                    # 单值字段却传进了列表：合并为字符串或取空
                    vals = ["; ".join([str(v) for v in vals if v])] if vals else [None]
            else:
                vals = [vals]

            rng_cls = sv.get_class(slot.range)
            enum_def = None
            if slot.range:
                if slot.range in sv.all_enums():
                    enum_def = sv.get_enum(slot.range)
            if multivalued:
                new_ann[field] = []
            else:
                new_ann[field] = None
            logging.debug(f"FIELD: {field} SLOT: {slot.name}")
            for val in vals:
                if not val:
                    continue
                logging.debug(f"   VAL: {val}")
                if isinstance(val, tuple):
                    # special case for pairs
                    if rng_cls is None:
                        logging.error(f"Cannot find class for inlined tuple range {slot.range}")
                        continue
                    sub_slots = sv.class_induced_slots(rng_cls.name)
                    obj = {}
                    for i in range(0, len(val)):
                        sub_slot = sub_slots[i]
                        sub_rng = sv.get_class(sub_slot.range)
                        if not sub_rng:
                            logging.error(f"Cannot find range for {sub_slot.name}")
                        if sub_slot.range is None:
                            logging.error(
                                f"Cannot normalize value for slot without range: {sub_slot.name}"
                            )
                            continue
                        result = self.normalize_named_entity(
                            val[i], cast(ElementName, sub_slot.range)
                        )
                        obj[sub_slot.name] = result
                elif isinstance(val, dict):
                    # 递归处理并彻底剔除子对象中的占位空值（如 "未明确指定"、"null"）
                    from ontogpt.utils.parse_utils import is_null_like_value
                    clean_dict = {vk: vv for vk, vv in val.items() if not is_null_like_value(vv)}
                    if not clean_dict:
                        continue
                    obj = self.ground_annotation_object(clean_dict, rng_cls) if rng_cls else clean_dict
                else:
                    from ontogpt.utils.parse_utils import is_null_like_value
                    if is_null_like_value(val):
                        continue
                    obj = self.normalize_named_entity(val, slot.range)  # type: ignore
                if enum_def:
                    found = False
                    logging.info(f"Looking for {obj} in {enum_def.name}")
                    permissible_values: List[str] = []
                    raw_permissible_values = enum_def.permissible_values
                    if isinstance(raw_permissible_values, dict):
                        permissible_values = [
                            str(permissible_value)
                            for permissible_value in raw_permissible_values.keys()
                        ]
                    elif isinstance(raw_permissible_values, list):
                        permissible_values = [
                            (
                                pv.get("text")
                                if isinstance(pv, dict) and isinstance(pv.get("text"), str)
                                else getattr(pv, "text", None)
                            )
                            or str(pv)
                            for pv in raw_permissible_values
                        ]
                    for permissible_value in permissible_values:
                        if isinstance(obj, str) and isinstance(permissible_value, str):
                            if obj.lower() == permissible_value.lower():
                                obj = permissible_value
                                found = True
                                break
                    if not found:
                        logging.info(f"Cannot find enum value for {obj} in {enum_def.name}")
                        obj = None
                if multivalued:
                    new_ann[field].append(obj)
                else:
                    new_ann[field] = obj
        logging.debug(f"Creating object from dict {new_ann}")
        logging.info(new_ann)
        py_cls = getattr(self._require_template_module(), class_name)
        return py_cls(**new_ann)

    def get_spans(self, input_text: str, named_entities: list[NamedEntity]) -> list[NamedEntity]:
        """
        Get the spans for the named entities in the input text.

        :param input_text: The full input text for the overall extraction
        :param extracted_object: The extracted object to be updated
        :return: The extracted object with spans
        """

        named_entities_with_spans = []

        for ne in named_entities:
            ne.original_spans = get_span_values(input_text, ne.label or "")
            named_entities_with_spans.append(ne)

        return named_entities_with_spans
