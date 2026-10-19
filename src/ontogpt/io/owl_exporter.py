"""OWL convertor."""

from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
from typing import TextIO, Union

import pydantic
from linkml.generators.pythongen import PythonGenerator
from linkml_owl.dumpers.owl_dumper import OWLDumper
from linkml_runtime import SchemaView

from ontogpt.io.exporter import Exporter
from ontogpt.templates.core import ExtractionResult


@dataclass
class OWLExporter(Exporter):
    def export(
        self,
        extraction_output: ExtractionResult,
        output: Union[str, Path, TextIO, BytesIO],
        schemaview: SchemaView,
        id_value=None,
    ):
        should_close = False
        if isinstance(output, Path):
            output = open(str(output), "w", encoding="utf-8")
            should_close = True
        elif isinstance(output, str):
            output = StringIO(output)

        from ontogpt.io.owl_builder import OWL2Builder

        schema_name = getattr(schemaview.schema, "name", None) or "knowledge_ontology"
        builder = OWL2Builder(schemaview=schemaview, schema_id=schema_name)
        g = builder.build_from_extraction(extraction_output, id_value=id_value)

        # 尝试补充 linkml_owl 的扩展公理（如有）
        if extraction_output.extracted_object:
            try:
                dumper = OWLDumper()
                element = extraction_output.extracted_output if hasattr(extraction_output, "extracted_output") else extraction_output.extracted_object
                element_as_dc = self._as_dataclass_object(element, schemaview)
                doc = dumper.to_ontology_document(element_as_dc, schemaview.schema)
                ont = getattr(doc, "ontology", doc)
                extra_axioms_xml = ont.save_to_string("owl") if hasattr(ont, "save_to_string") else str(doc)
                if extra_axioms_xml and ("<owl:Class" in extra_axioms_xml or "<owl:Axiom" in extra_axioms_xml):
                    g.parse(data=extra_axioms_xml, format="xml")
            except Exception:
                pass

        xml_str = g.serialize(format="pretty-xml", encoding="utf-8").decode("utf-8")
        output.write(xml_str)
        if should_close:
            output.close()

    def _as_dataclass_object(self, element: pydantic.BaseModel, schemaview: SchemaView):
        cls_name = type(element).__name__
        schemaview.merge_imports()
        element_dict = element.model_dump()
        dataclasses_module = PythonGenerator(schemaview.schema).compile_module()
        target_class_py = dataclasses_module.__dict__[cls_name]
        element_as_dataclass = target_class_py(**element_dict)
        return element_as_dataclass
