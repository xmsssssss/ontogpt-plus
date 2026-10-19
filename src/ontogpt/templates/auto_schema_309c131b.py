from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.12.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'auto_schema_309c131b',
     'default_range': 'string',
     'description': '本模式用于从电力行业（特别是燃机领域）的技术文档中提取结构化信息。 This schema is designed to '
                    'extract structured information from technical documentation '
                    'in the power industry, specifically focusing on gas turbine '
                    'specifications, components, processes, and operational '
                    'parameters.',
     'id': 'https://w3id.org/ontogpt/auto_schema_309c131b',
     'imports': ['linkml:types', 'core'],
     'name': 'auto_schema_309c131b',
     'prefixes': {'auto_schema_309c131b': {'prefix_prefix': 'auto_schema_309c131b',
                                           'prefix_reference': 'https://w3id.org/ontogpt/auto_schema_309c131b/'},
                  'core': {'prefix_prefix': 'core',
                           'prefix_reference': 'https://w3id.org/ontogpt/core/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'src\\ontogpt\\templates\\auto_schema_309c131b.yaml',
     'title': 'Gas Turbine Technical Specifications and Components'} )

class TermValidationStatus(str, Enum):
    """
    Outcome categories for ontology term validation.
    """
    VALID = "VALID"
    """
    The identifier resolves and the extracted label is its label or a synonym
    """
    LABEL_DIFFERS = "LABEL_DIFFERS"
    """
    The identifier resolves but the extracted label is neither its label nor a synonym
    """
    REPLACED = "REPLACED"
    """
    The identifier was invalid or obsolete and a valid substitute was found
    """
    UNRESOLVED = "UNRESOLVED"
    """
    The identifier was invalid and no substitute was found; the value was rewritten with the auto prefix
    """
    SKIPPED = "SKIPPED"
    """
    The identifier could not be checked because no ontology adapter was available for its prefix
    """


class NullDataOptions(str, Enum):
    UNSPECIFIED_METHOD_OF_ADMINISTRATION = "UNSPECIFIED_METHOD_OF_ADMINISTRATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_MENTIONED = "NOT_MENTIONED"



class ExtractionResult(ConfiguredBaseModel):
    """
    A result of extracting knowledge on text
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    input_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    input_title: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    input_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    raw_completion_output: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    prompt: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    extracted_object: Optional[Any] = Field(default=None, description="""The complex objects extracted from the text""", json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    named_entities: Optional[list[Any]] = Field(default=None, description="""Named entities extracted from the text""", json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })
    validation: Optional[TermValidationReport] = Field(default=None, description="""Results of validating the grounded terms in the extracted object against their source ontologies, including any replacements made. Absent when validation was not run.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ExtractionResult']} })


class TermValidationReport(ConfiguredBaseModel):
    """
    Summary of ontology term validation performed on an extraction result. Each grounded identifier in the extracted object is checked for existence and obsolescence in its ontology and for agreement between the extracted label and the ontology's label or synonyms. Invalid identifiers are replaced when a valid substitute can be found.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    validator: Optional[str] = Field(default=None, description="""Name and version of the validation library used""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    total_terms: Optional[int] = Field(default=None, description="""Number of grounded identifiers examined""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    valid_terms: Optional[int] = Field(default=None, description="""Identifiers that resolved with a matching label or synonym""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    replaced_terms: Optional[int] = Field(default=None, description="""Identifiers replaced with a valid substitute""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    unresolved_terms: Optional[int] = Field(default=None, description="""Invalid identifiers for which no substitute was found; these are rewritten with the auto prefix so that no invalid identifier remains""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    label_mismatches: Optional[int] = Field(default=None, description="""Identifiers that resolved but whose extracted label is neither the ontology label nor a known synonym; kept as they are""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    skipped_terms: Optional[int] = Field(default=None, description="""Identifiers that could not be checked because no ontology adapter was available""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })
    results: Optional[list[TermValidationResult]] = Field(default=None, description="""One entry per examined identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationReport']} })


class TermValidationResult(ConfiguredBaseModel):
    """
    Outcome of validating one grounded identifier.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    original_id: Optional[str] = Field(default=None, description="""The identifier as produced by grounding""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    label: Optional[str] = Field(default=None, description="""The label extracted from the text for this identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult', 'NamedEntity']} })
    entity_class: Optional[str] = Field(default=None, description="""The template class the identifier was grounded for""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    status: Optional[TermValidationStatus] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    ontology_label: Optional[str] = Field(default=None, description="""The label of the original identifier in its ontology, when it resolved""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    replacement_id: Optional[str] = Field(default=None, description="""The identifier substituted into the output, if any""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    replacement_label: Optional[str] = Field(default=None, description="""The ontology label of the replacement identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    message: Optional[str] = Field(default=None, description="""Human-readable explanation of the outcome""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })
    attempts: Optional[list[str]] = Field(default=None, description="""Candidate identifiers considered while searching for a replacement""", json_schema_extra = { "linkml_meta": {'domain_of': ['TermValidationResult']} })


class NamedEntity(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'http://w3id.org/ontogpt/core'})

    id: str = Field(default=..., description="""A unique identifier for the named entity""", json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'comments': ['this is populated during the grounding and normalization step'],
         'domain_of': ['NamedEntity', 'Publication', 'AutoSchema309c131bReport']} })
    label: Optional[str] = Field(default=None, description="""The label (name) of the named thing""", json_schema_extra = { "linkml_meta": {'aliases': ['name'],
         'annotations': {'owl': {'tag': 'owl',
                                 'value': 'AnnotationProperty, AnnotationAssertion'}},
         'domain_of': ['TermValidationResult', 'NamedEntity'],
         'slot_uri': 'rdfs:label'} })
    original_spans: Optional[list[str]] = Field(default=None, description="""The coordinates of the original text span from which the named entity was extracted, inclusive. For example, \"10:25\" means the span starting from the 10th character and ending with the 25th character. The first character in the text has index 0. Newlines are treated as single characters. Multivalued as there may be multiple spans for a single text.""", json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'comments': ['This is determined during grounding and normalization',
                      'But is based on the full input text'],
         'domain_of': ['NamedEntity']} })

    @field_validator('original_spans')
    def pattern_original_spans(cls, v):
        pattern=re.compile(r"^\d+:\d+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid original_spans format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid original_spans format: {v}"
            raise ValueError(err_msg)
        return v


class CompoundExpression(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'http://w3id.org/ontogpt/core'})

    pass


class Triple(CompoundExpression):
    """
    Abstract parent for Relation Extraction tasks
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'abstract': True, 'from_schema': 'http://w3id.org/ontogpt/core'})

    subject: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })
    predicate: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })
    object: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })
    qualifier: Optional[str] = Field(default=None, description="""A qualifier for the statements, e.g. \"NOT\" for negation""", json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })
    subject_qualifier: Optional[str] = Field(default=None, description="""An optional qualifier or modifier for the subject of the statement, e.g. \"high dose\" or \"intravenously administered\"""", json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })
    object_qualifier: Optional[str] = Field(default=None, description="""An optional qualifier or modifier for the object of the statement, e.g. \"severe\" or \"with additional complications\"""", json_schema_extra = { "linkml_meta": {'domain_of': ['Triple']} })


class TextWithTriples(ConfiguredBaseModel):
    """
    A text containing one or more relations of the Triple type.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    publication: Optional[Publication] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'domain_of': ['TextWithTriples', 'TextWithEntity']} })
    triples: Optional[list[Triple]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['TextWithTriples']} })


class TextWithEntity(ConfiguredBaseModel):
    """
    A text containing one or more instances of a single type of entity.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    publication: Optional[Publication] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'domain_of': ['TextWithTriples', 'TextWithEntity']} })
    entities: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['TextWithEntity']} })


class RelationshipType(NamedEntity):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core',
         'id_prefixes': ['RO', 'biolink']})

    id: str = Field(default=..., description="""A unique identifier for the named entity""", json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'comments': ['this is populated during the grounding and normalization step'],
         'domain_of': ['NamedEntity', 'Publication', 'AutoSchema309c131bReport']} })
    label: Optional[str] = Field(default=None, description="""The label (name) of the named thing""", json_schema_extra = { "linkml_meta": {'aliases': ['name'],
         'annotations': {'owl': {'tag': 'owl',
                                 'value': 'AnnotationProperty, AnnotationAssertion'}},
         'domain_of': ['TermValidationResult', 'NamedEntity'],
         'slot_uri': 'rdfs:label'} })
    original_spans: Optional[list[str]] = Field(default=None, description="""The coordinates of the original text span from which the named entity was extracted, inclusive. For example, \"10:25\" means the span starting from the 10th character and ending with the 25th character. The first character in the text has index 0. Newlines are treated as single characters. Multivalued as there may be multiple spans for a single text.""", json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': 'true'}},
         'comments': ['This is determined during grounding and normalization',
                      'But is based on the full input text'],
         'domain_of': ['NamedEntity']} })

    @field_validator('original_spans')
    def pattern_original_spans(cls, v):
        pattern=re.compile(r"^\d+:\d+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid original_spans format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid original_spans format: {v}"
            raise ValueError(err_msg)
        return v


class Publication(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    id: Optional[str] = Field(default=None, description="""The publication identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedEntity', 'Publication', 'AutoSchema309c131bReport']} })
    title: Optional[str] = Field(default=None, description="""The title of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    abstract: Optional[str] = Field(default=None, description="""The abstract of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    combined_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    full_text: Optional[str] = Field(default=None, description="""The full text of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })


class AnnotatorResult(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    subject_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })
    object_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })
    object_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })


class AutoSchema309c131bReport(ConfiguredBaseModel):
    """
    根类，代表一份完整的燃机技术报告或规格说明书。 Root class representing a complete gas turbine technical report or specification sheet.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b',
         'tree_root': True})

    id: str = Field(default=..., description="""Unique auto identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedEntity', 'Publication', 'AutoSchema309c131bReport']} })
    equipment_components: Optional[list[EquipmentComponent]] = Field(default=None, description="""提取文本中提到的所有硬件设备、部件或子系统。 Extract all hardware devices, parts, or subsystems mentioned in the text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    technical_processes: Optional[list[TechnicalProcess]] = Field(default=None, description="""提取涉及的操作过程、燃烧方式、冷却机制或控制逻辑。 Extract operational processes, combustion methods, cooling mechanisms, or control logic described.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    performance_parameters: Optional[list[PerformanceParameter]] = Field(default=None, description="""提取具体的数值指标、等级数量、流量分配或技术参数。 Extract specific numerical metrics, stage counts, flow allocations, or technical specifications.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    material_properties: Optional[list[MaterialProperty]] = Field(default=None, description="""提取关于材料涂层、耐腐蚀性、机械性能或叶片材质的描述。 Extract descriptions regarding material coatings, corrosion resistance, mechanical properties, or blade materials.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    operational_modes: Optional[list[OperationalMode]] = Field(default=None, description="""提取机组的运行状态、启动条件、旋转方向或工况要求。 Extract operational states, start-up conditions, rotation directions, or operating requirements.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    system_configurations: Optional[list[SystemConfiguration]] = Field(default=None, description="""提取机组的整体配置、型号及联合循环结构等系统级参数。 Extract overall unit configuration, model numbers, and combined cycle structures.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    auxiliary_systems: Optional[list[AuxiliarySystem]] = Field(default=None, description="""提取润滑油、密封油、冷却水等辅助系统的组件、逻辑及特性。 Extract components, logic, and characteristics of auxiliary systems like lubrication, sealing, cooling water, etc.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    electrical_control_specs: Optional[list[ElectricalControlSpec]] = Field(default=None, description="""提取励磁、AVR、SFC及电气保护相关的技术参数与逻辑。 Extract technical parameters and logic related to excitation, AVR, SFC, and electrical protection.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    safety_and_operation_procedures: Optional[list[SafetyOperationProcedure]] = Field(default=None, description="""提取安全规程、试验标准、监护要求及异常处理流程。 Extract safety regulations, test standards, supervision requirements, and abnormal handling procedures.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    chemical_water_quality: Optional[list[ChemicalWaterQuality]] = Field(default=None, description="""提取汽水品质、氢气纯度、露点及化学取样标准。 Extract steam/water quality, hydrogen purity, dew point, and chemical sampling standards.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    maintenance_storage_procedures: Optional[list[MaintenanceStorageProcedure]] = Field(default=None, description="""提取停机保养分类、防锈蚀范围及充氮/烘干原理。 Extract shutdown maintenance categories, anti-corrosion scope, and nitrogen/drying principles.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })
    auto_discovered_features: Optional[list[KeyValuePair]] = Field(default=None, description="""动态未归类特征键值对""", json_schema_extra = { "linkml_meta": {'domain_of': ['AutoSchema309c131bReport']} })


class EquipmentComponent(CompoundExpression):
    """
    表示燃机的具体物理组成部分，如压气机、燃烧室、透平、管线等。 Represents specific physical components of the gas turbine, such as compressors, combustors, turbines, pipelines, etc.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    name: Optional[str] = Field(default=None, description="""部件名称 (e.g., \"轴流式压气机\", \"过渡段\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    component_type: Optional[str] = Field(default=None, description="""部件类型分类 (e.g., \"Core Component\", \"Fuel System\", \"Control Unit\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    quantity_or_stages: Optional[str] = Field(default=None, description="""数量或级数 (e.g., \"17 级\", \"20 只\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    arrangement: Optional[str] = Field(default=None, description="""布置方式 (e.g., \"环形布置\", \"沿轴线\", \"膨胀节连接HRSG\") Arrangement method including structural connections like expansion joints.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    key_feature: Optional[str] = Field(default=None, description="""关键特性 (e.g., \"带有进口可调导叶(IGV)\", \"反动式叶片\", \"管壳式加热器\") Key features including specific design types like heat exchanger styles.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    function_description: Optional[str] = Field(default=None, description="""功能简述""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    cooling_source: Optional[str] = Field(default=None, description="""冷却来源 (e.g., \"压气机部分排气\", \"强迫油循环风冷\") Source of cooling medium or method for the component.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })
    valve_mechanism: Optional[str] = Field(default=None, description="""阀门触发或控制机制 (e.g., \"电磁阀控制空气\", \"全弹簧机构避免渗漏\") Trigger mechanism or actuation method for valves within this component.""", json_schema_extra = { "linkml_meta": {'domain_of': ['EquipmentComponent']} })


class TechnicalProcess(CompoundExpression):
    """
    表示技术操作、燃烧工艺、控制策略或流体动力学过程。 Represents technical operations, combustion processes, control strategies, or fluid dynamic processes.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    process_name: Optional[str] = Field(default=None, description="""过程名称 (e.g., \"干式低NOX燃烧技术\", \"火焰稳定性维持\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['TechnicalProcess']} })
    mechanism: Optional[str] = Field(default=None, description="""作用机理 (e.g., \"旁路阀将一部分压气机排气排入...\", \"叶轮流速正比于燃气流速\") Mechanism of action, potentially including sensor principles if applicable to the process context.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TechnicalProcess']} })
    purpose: Optional[str] = Field(default=None, description="""目的或效果 (e.g., \"提高机组启动时的火焰稳定性\", \"改进耐腐蚀能力\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['TechnicalProcess']} })
    control_method: Optional[str] = Field(default=None, description="""控制方法 (e.g., \"由安装在燃料单元中的控制阀控制\", \"高压油控制IGV\") Control method, specifying media like hydraulic oil if relevant.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TechnicalProcess']} })


class PerformanceParameter(CompoundExpression):
    """
    表示可量化的技术指标、参数设定或流量分配。 Represents quantitative technical indicators, parameter settings, or flow distributions.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    parameter_name: Optional[str] = Field(default=None, description="""参数名称 (e.g., \"燃料管线分配\", \"燃空比\")""", json_schema_extra = { "linkml_meta": {'domain_of': ['PerformanceParameter']} })
    value_or_distribution: Optional[str] = Field(default=None, description="""具体数值或分布情况 (e.g., \"四条燃料管线：值班管线、主A管线...\", \"3根平衡管\") Specific values or distributions,""", json_schema_extra = { "linkml_meta": {'domain_of': ['PerformanceParameter']} })


class MaterialProperty(CompoundExpression):
    """
    描述材料的物理和化学属性。 Represents material physical and chemical properties.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    material_name: Optional[str] = Field(default=None, description="""材料名称""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaterialProperty']} })
    property_type: Optional[str] = Field(default=None, description="""属性类型 (e.g., Corrosion Resistance, Hardness)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaterialProperty']} })
    value: Optional[str] = Field(default=None, description="""属性值或等级""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaterialProperty', 'KeyValuePair']} })


class OperationalMode(CompoundExpression):
    """
    描述机组的运行状态或启动条件。 Represents operational states or startup conditions.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    mode_name: Optional[str] = Field(default=None, description="""模式名称 (e.g., Startup, Shutdown)""", json_schema_extra = { "linkml_meta": {'domain_of': ['OperationalMode']} })
    condition_requirements: Optional[str] = Field(default=None, description="""条件要求 (e.g., Prohibition conditions, Prerequisites)""", json_schema_extra = { "linkml_meta": {'domain_of': ['OperationalMode']} })
    status_indicator: Optional[str] = Field(default=None, description="""状态指示 (e.g., CRT display contents)""", json_schema_extra = { "linkml_meta": {'domain_of': ['OperationalMode']} })


class SystemConfiguration(CompoundExpression):
    """
    描述系统级配置和结构。 Represents system-level configurations and structures.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    config_name: Optional[str] = Field(default=None, description="""配置名称""", json_schema_extra = { "linkml_meta": {'domain_of': ['SystemConfiguration']} })
    structure_details: Optional[str] = Field(default=None, description="""结构细节""", json_schema_extra = { "linkml_meta": {'domain_of': ['SystemConfiguration']} })


class AuxiliarySystem(CompoundExpression):
    """
    描述辅助系统及其特性。 Represents auxiliary systems and their characteristics.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    system_name: Optional[str] = Field(default=None, description="""系统名称""", json_schema_extra = { "linkml_meta": {'domain_of': ['AuxiliarySystem']} })
    components_list: Optional[str] = Field(default=None, description="""组件列表""", json_schema_extra = { "linkml_meta": {'domain_of': ['AuxiliarySystem']} })
    operational_logic: Optional[str] = Field(default=None, description="""运行逻辑""", json_schema_extra = { "linkml_meta": {'domain_of': ['AuxiliarySystem']} })


class ElectricalControlSpec(CompoundExpression):
    """
    描述电气控制和保护规范。 Represents electrical control and protection specifications.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    spec_category: Optional[str] = Field(default=None, description="""规范类别 (e.g., Excitation, Protection)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ElectricalControlSpec']} })
    parameters: Optional[str] = Field(default=None, description="""具体参数""", json_schema_extra = { "linkml_meta": {'domain_of': ['ElectricalControlSpec']} })
    check_items: Optional[str] = Field(default=None, description="""检查项目 (e.g., GIS SF6 pressure, Battery float charge)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ElectricalControlSpec']} })


class SafetyOperationProcedure(CompoundExpression):
    """
    描述安全操作规程、试验标准及异常处理流程。 Represents safety operation procedures, test standards, and abnormal handling workflows.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    procedure_name: Optional[str] = Field(default=None, description="""规程名称 (e.g., 安全门校验, 超速试验)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    handling_workflow: Optional[str] = Field(default=None, description="""异常处理流程 (e.g., 立即停止待故障消除)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    supervision_requirement: Optional[str] = Field(default=None, description="""监护要求 (e.g., 双人监护, 容器外设专人)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    division_of_duties: Optional[str] = Field(default=None, description="""分工职责 (e.g., 热工为主运行配合)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    acceptance_criteria: Optional[str] = Field(default=None, description="""合格标准 (e.g., 两次动作值之差<18rpm)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    prerequisites: Optional[str] = Field(default=None, description="""前提条件 (e.g., HPCV/IPCV严密性试验前提)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    risk_identification: Optional[str] = Field(default=None, description="""风险识别与应对 (e.g., 虚假水位, 金属冷冲击)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    inspection_tools: Optional[str] = Field(default=None, description="""检查工具或方法 (e.g., 听音棒, 气体探测仪)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })
    leakage_check_scope: Optional[str] = Field(default=None, description="""泄漏检查范围 (e.g., 四漏检查)""", json_schema_extra = { "linkml_meta": {'domain_of': ['SafetyOperationProcedure']} })


class ChemicalWaterQuality(CompoundExpression):
    """
    描述化学介质（水、汽、氢）的品质标准和取样要求。 Represents quality standards and sampling requirements for chemical media (water, steam, hydrogen).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    medium_type: Optional[str] = Field(default=None, description="""介质类型 (e.g., 除盐水, 凝结水, 氢气, 给水)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ChemicalWaterQuality']} })
    quality_standard: Optional[str] = Field(default=None, description="""质量标准 (e.g., 纯度>96%, 露点-25~0℃, pH值)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ChemicalWaterQuality']} })
    sampling_conditions: Optional[str] = Field(default=None, description="""取样条件 (e.g., 流速40~60L/h, 温度25~35℃)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ChemicalWaterQuality']} })
    adjustment_strategy: Optional[str] = Field(default=None, description="""调节策略 (e.g., 根据水质调整连排门)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ChemicalWaterQuality']} })
    limit_values: Optional[str] = Field(default=None, description="""限值 (e.g., 氢压0.35MPa)""", json_schema_extra = { "linkml_meta": {'domain_of': ['ChemicalWaterQuality']} })


class MaintenanceStorageProcedure(CompoundExpression):
    """
    描述停机保养、防腐存储的原理和分类。 Represents shutdown maintenance, preservation principles, and classifications.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    maintenance_category: Optional[str] = Field(default=None, description="""保养分类 (e.g., 调峰<48h, 短期48h-30d, 长期30d-90d)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaintenanceStorageProcedure']} })
    preservation_method: Optional[str] = Field(default=None, description="""防腐方法 (e.g., 氮气覆盖法, 干法充氮, 氨水碱化烘干)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaintenanceStorageProcedure']} })
    principle_explanation: Optional[str] = Field(default=None, description="""原理说明 (e.g., 维持正压阻碍空气, PH值高导致溶解)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaintenanceStorageProcedure']} })
    scope_definition: Optional[str] = Field(default=None, description="""范围界定 (e.g., 锅炉、汽机、燃机等)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaintenanceStorageProcedure']} })
    responsibility_assignment: Optional[str] = Field(default=None, description="""职责分工 (e.g., 主控制室与项目部)""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaintenanceStorageProcedure']} })


class KeyValuePair(ConfiguredBaseModel):
    """
    通用键值对结构，用于存储未预定义的动态特征。 General key-value pair structure for storing undefined dynamic features.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/auto_schema_309c131b'})

    key: Optional[str] = Field(default=None, description="""特征名称或键名""", json_schema_extra = { "linkml_meta": {'domain_of': ['KeyValuePair']} })
    value: Optional[str] = Field(default=None, description="""特征取值或内容""", json_schema_extra = { "linkml_meta": {'domain_of': ['MaterialProperty', 'KeyValuePair']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
ExtractionResult.model_rebuild()
TermValidationReport.model_rebuild()
TermValidationResult.model_rebuild()
NamedEntity.model_rebuild()
CompoundExpression.model_rebuild()
Triple.model_rebuild()
TextWithTriples.model_rebuild()
TextWithEntity.model_rebuild()
RelationshipType.model_rebuild()
Publication.model_rebuild()
AnnotatorResult.model_rebuild()
AutoSchema309c131bReport.model_rebuild()
EquipmentComponent.model_rebuild()
TechnicalProcess.model_rebuild()
PerformanceParameter.model_rebuild()
MaterialProperty.model_rebuild()
OperationalMode.model_rebuild()
SystemConfiguration.model_rebuild()
AuxiliarySystem.model_rebuild()
ElectricalControlSpec.model_rebuild()
SafetyOperationProcedure.model_rebuild()
ChemicalWaterQuality.model_rebuild()
MaintenanceStorageProcedure.model_rebuild()
KeyValuePair.model_rebuild()
