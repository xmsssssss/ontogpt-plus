import sys, rdflib
from ontogpt.webapp.main import task_storage
sys.stdout.reconfigure(encoding='utf-8')

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
raw_owl = detail['result'].get('owl_output', '')
g = rdflib.Graph()
g.parse(data=raw_owl, format='xml')

named_inds = list(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual))
print("Total named individuals in task efd3b5c4:", len(named_inds))
print("Sample URIs in efd3b5c4:")
for ind in named_inds[:5]:
    print(" -", ind)
