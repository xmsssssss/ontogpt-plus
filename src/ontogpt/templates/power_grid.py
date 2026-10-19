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


metamodel_version = "1.11.0"
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


linkml_meta = LinkMLMeta({'default_prefix': 'power',
     'default_range': 'string',
     'description': '����ϵͳ�豸̨�ˡ��������ˡ��̵籣����������������ȱ�ݡ�����Ӧ״̬��������޴��ó�ȡģ��',
     'id': 'https://w3id.org/ontogpt/power_grid',
     'imports': ['linkml:types', 'core'],
     'name': 'power_grid',
     'prefixes': {'AUTO': {'prefix_prefix': 'AUTO',
                           'prefix_reference': 'http://example.org/auto/'},
                  'cim': {'prefix_prefix': 'cim',
                          'prefix_reference': 'http://iec.ch/TC57/CIM#'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'power': {'prefix_prefix': 'power',
                            'prefix_reference': 'http://example.org/power/'}},
     'source_file': 'src/ontogpt/templates/power_grid.yaml',
     'title': 'Power Grid System, Equipment and Fault Analysis Template'} )

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


class VoltageLevelEnum(str, Enum):
    """
    ��Ƶ�ѹ�ȼ�
    """
    AC_1000kV = "AC_1000kV"
    """
    �ظ�ѹ����1000kV
    """
    AC_750kV = "AC_750kV"
    """
    ����ѹ����750kV
    """
    AC_500kV = "AC_500kV"
    """
    ����ѹ����500kV
    """
    AC_330kV = "AC_330kV"
    """
    ����330kV
    """
    AC_220kV = "AC_220kV"
    """
    ��ѹ����220kV
    """
    AC_110kV = "AC_110kV"
    """
    ��ѹ����110kV
    """
    AC_35kV = "AC_35kV"
    """
    ��ѹ����35kV
    """
    AC_10kV = "AC_10kV"
    """
    ��ѹ���10kV
    """
    AC_0FULL_STOP4kV = "AC_0.4kV"
    """
    ��ѹ���0.4kV
    """
    DC_800kV = "DC_800kV"
    """
    �ظ�ѹֱ����800kV
    """
    DC_500kV = "DC_500kV"
    """
    ֱ����500kV
    """


class DefectSeverityEnum(str, Enum):
    """
    ȱ�����س̶ȼ��𣨹�����׼��
    """
    Critical = "Critical"
    """
    Σ��ȱ��
    """
    Serious = "Serious"
    """
    ����ȱ��
    """
    General = "General"
    """
    һ��ȱ��
    """
    Normal = "Normal"
    """
    ��������
    """



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
         'domain_of': ['NamedEntity', 'Publication', 'PowerGridAnalysisReport']} })
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
         'domain_of': ['NamedEntity', 'Publication', 'PowerGridAnalysisReport']} })
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

    id: Optional[str] = Field(default=None, description="""The publication identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['NamedEntity', 'Publication', 'PowerGridAnalysisReport']} })
    title: Optional[str] = Field(default=None, description="""The title of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    abstract: Optional[str] = Field(default=None, description="""The abstract of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    combined_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })
    full_text: Optional[str] = Field(default=None, description="""The full text of the publication""", json_schema_extra = { "linkml_meta": {'domain_of': ['Publication']} })


class AnnotatorResult(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://w3id.org/ontogpt/core'})

    subject_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })
    object_id: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })
    object_text: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['AnnotatorResult']} })


class PowerGridAnalysisReport(ConfiguredBaseModel):
    """
    �����¹���բ���������վȱ��Ѳ�졢���鱨���������м�¼
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid', 'tree_root': True})

    id: str = Field(default="AUTO:_ROOT", description="""������¹�Ψһ��ʶ���""", json_schema_extra = { "linkml_meta": {'annotations': {'prompt.skip': {'tag': 'prompt.skip', 'value': True}},
         'domain_of': ['NamedEntity', 'Publication', 'PowerGridAnalysisReport'],
         'ifabsent': 'string(AUTO:_ROOT)'} })
    event_title: Optional[str] = Field(default=None, description="""�¹ʻ򱨸��Ҫ����""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'AnnotationProperty, AnnotationAssertion'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    occurrence_time: Optional[str] = Field(default=None, description="""���Ϸ�����ȱ�ݷ���ʱ��""", json_schema_extra = { "linkml_meta": {'domain_of': ['PowerGridAnalysisReport']} })
    location: Optional[str] = Field(default=None, description="""�漰�ı��վ������վ������վ����·���Σ��� 500kV�ϲ����վ��220kV�Ӳ��ߣ�""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'AnnotationProperty, AnnotationAssertion'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    voltage_level: Optional[VoltageLevelEnum] = Field(default=None, description="""��ѹ�ȼ�""", json_schema_extra = { "linkml_meta": {'domain_of': ['PowerGridAnalysisReport']} })
    grid_topology_info: Optional[str] = Field(default=None, description="""�������з�ʽ��һ�����˽�����ʽ���� ˫ĸ�ߡ����Ž��ߡ�3/2��·�����ߣ�""", json_schema_extra = { "linkml_meta": {'domain_of': ['PowerGridAnalysisReport']} })
    primary_equipment: Optional[list[PrimaryEquipment]] = Field(default=None, description="""�漰�ı�ѹ������·����GIS�����뿪�ء��������������������µ�һ���豸�б�""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    secondary_system: Optional[list[SecondarySystem]] = Field(default=None, description="""�漰�ļ̵籣��װ�á����װ�á���ȫ�Զ�װ�û������ն��б�""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    fault_incident: Optional[FaultIncidentDetail] = Field(default=None, description="""����ȱ�����顢����������س̶�""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    relay_protection_actions: Optional[list[ProtectionAction]] = Field(default=None, description="""�̵籣���밲ȫ�Զ�װ�ö�����Ϊ���� ���ʲ�ٶ϶��������򱣻���բ���Զ��غ�բ������""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    measurements_and_indicators: Optional[list[MeasurementItem]] = Field(default=None, description="""�ؼ���������������ָ�꣨�� ���ϵ�����ֵ��SF6΢ˮ�������ܽ��������DGA�������²�ȣ�""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    auto_discovered_features: Optional[list[KeyValuePair]] = Field(default=None, description="""���ĵ�������Ӧ��ȡ������רҵ������������������ҵ���ר������""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl',
                                 'value': 'ObjectProperty, ObjectSomeValuesFrom'}},
         'domain_of': ['PowerGridAnalysisReport']} })
    dispatch_and_switching_ops: Optional[list[str]] = Field(default=None, description="""���ȴ��ü���բ�������裨�� ������ϼ���ת�Ƹ��ɡ�������բ���ҽӵ��ߣ�""", json_schema_extra = { "linkml_meta": {'domain_of': ['PowerGridAnalysisReport']} })
    maintenance_actions: Optional[list[str]] = Field(default=None, description="""�ֳ����޴����ʩ�����Ľ��飨�� ��Ե����ɨ���߼н�̡������׹ܡ����˹��ˣ�""", json_schema_extra = { "linkml_meta": {'domain_of': ['PowerGridAnalysisReport']} })


class PrimaryEquipment(CompoundExpression):
    """
    һ���豸ʵ��
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    name: Optional[str] = Field(default=None, description="""�豸ȫ������ȱ�ţ���""", json_schema_extra = { "linkml_meta": {'domain_of': ['PrimaryEquipment']} })
    equipment_category: Optional[str] = Field(default=None, description="""�豸רҵ���ࣨ�� ��ѹ��, ��·��, ���뿪��, GIS, ������, ����������, ��ѹ������, �翹��, �����·, �������£�""", json_schema_extra = { "linkml_meta": {'domain_of': ['PrimaryEquipment']} })
    bay_name: Optional[str] = Field(default=None, description="""���ڼ������""", json_schema_extra = { "linkml_meta": {'domain_of': ['PrimaryEquipment']} })
    component_involved: Optional[str] = Field(default=None, description="""������ϻ��춯�������� ��ѹ��A���׹ܡ��ֽӿ��ء��������ҡ������䣩""", json_schema_extra = { "linkml_meta": {'domain_of': ['PrimaryEquipment']} })


class SecondarySystem(CompoundExpression):
    """
    ����ϵͳ��̵籣��ʵ��
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    device_name: Optional[str] = Field(default=None, description="""�������Զ���װ�����Ƽ��ͺţ��� RCS-978��ѹ�������װ�á�CSC-103��·������""", json_schema_extra = { "linkml_meta": {'domain_of': ['SecondarySystem']} })
    device_type: Optional[str] = Field(default=None, description="""�����豸���ͣ��� ������, �󱸱���, ����Ͷװ��, ����¼����, ��ص�Ԫ��""", json_schema_extra = { "linkml_meta": {'domain_of': ['SecondarySystem']} })


class FaultIncidentDetail(CompoundExpression):
    """
    ����ȱ������
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    defect_severity: Optional[DefectSeverityEnum] = Field(default=None, description="""ȱ�����س̶�""", json_schema_extra = { "linkml_meta": {'domain_of': ['FaultIncidentDetail']} })
    fault_phase: Optional[str] = Field(default=None, description="""������������ʣ��� A�൥��ӵء�AB���·�������·��""", json_schema_extra = { "linkml_meta": {'domain_of': ['FaultIncidentDetail']} })
    fault_phenomenon: Optional[str] = Field(default=None, description="""�ֳ�ֱ�۱��ֻ�澯�źţ��� ��˹���������澯���ŵ�𻨡���ͷ���ȱ�ɫ�������ܶ���""", json_schema_extra = { "linkml_meta": {'domain_of': ['FaultIncidentDetail']} })
    root_cause: Optional[str] = Field(default=None, description="""����������� �׻�����ѹ���¾�Ե���硢�񺦡��ܳ��ϻ�����е��ɬ��""", json_schema_extra = { "linkml_meta": {'domain_of': ['FaultIncidentDetail']} })


class ProtectionAction(CompoundExpression):
    """
    �̵籣���밲ȫ�Զ�װ�ö����߼�
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    protection_name: Optional[str] = Field(default=None, description="""�����ľ��屣�����ܶΣ��� ���˵������������Ƶ�����Ρ�������ʱ��������Ƶ���أ�""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProtectionAction']} })
    trip_breaker: Optional[str] = Field(default=None, description="""�����Ķ�·����ţ��� ����5011��5012��·����""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProtectionAction']} })
    reclose_result: Optional[str] = Field(default=None, description="""�غ�բ����������� �غϳɹ����غϲ��ɹ��������բ�����������غ�բ��""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProtectionAction']} })


class MeasurementItem(CompoundExpression):
    """
    ����������״̬�����ֵ
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    parameter_name: Optional[str] = Field(default=None, description="""����������������ƣ��� �����������������������ȲC2H2��SF6΢ˮ�����¡��ӵص��裩""", json_schema_extra = { "linkml_meta": {'domain_of': ['MeasurementItem']} })
    value_with_unit: Optional[str] = Field(default=None, description="""������ֵ����λ���� 18.5kA, 120ppm, 0.45MPa, 78��, 0.35����""", json_schema_extra = { "linkml_meta": {'domain_of': ['MeasurementItem']} })


class KeyValuePair(CompoundExpression):
    """
    ����Ӧ���ֵ�ר�����Լ�ֵ��
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ontogpt/power_grid'})

    key: Optional[str] = Field(default=None, description="""ר������������ �����¶ȡ��׹ܽ���tg�ġ��ֲ��ŵ������̵�����������ʱ�䣩""", json_schema_extra = { "linkml_meta": {'domain_of': ['KeyValuePair']} })
    value: Optional[str] = Field(default=None, description="""����ֵ���������""", json_schema_extra = { "linkml_meta": {'domain_of': ['KeyValuePair']} })


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
PowerGridAnalysisReport.model_rebuild()
PrimaryEquipment.model_rebuild()
SecondarySystem.model_rebuild()
FaultIncidentDetail.model_rebuild()
ProtectionAction.model_rebuild()
MeasurementItem.model_rebuild()
KeyValuePair.model_rebuild()
