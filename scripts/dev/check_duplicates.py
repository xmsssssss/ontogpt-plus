import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

print("=== Checking entities related to '励磁系统' ===")
for s in set(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual)):
    s_clean = unquote(str(s))
    if "励磁系统" in s_clean:
        types = [str(t).split('/')[-1] for t in g.objects(s, rdflib.RDF.type) if t != rdflib.OWL.NamedIndividual]
        props = {str(p).split('/')[-1]: unquote(str(o)) for p, o in g.predicate_objects(s) if p not in [rdflib.RDF.type, rdflib.RDFS.label]}
        print(f"Subject: {s_clean.split('/')[-1]} | Class: {types}")
        for k, v in props.items():
            print(f"    {k}: {repr(v)}")
