import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

print("Sample entities with '润滑油系统':")
for s in set(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual)):
    s_clean = unquote(str(s)).split('/')[-1]
    if "润滑油系统" in s_clean:
        props = {str(p).split('/')[-1]: unquote(str(o)) for p, o in g.predicate_objects(s) if p not in [rdflib.RDF.type, rdflib.RDFS.label]}
        print(f"[{s_clean}] -> {props}")
