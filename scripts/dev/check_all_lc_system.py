import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

print("All entities mentioning 励磁系统:")
for s in set(g.subjects()):
    s_clean = unquote(str(s))
    props = {str(p).split('/')[-1]: unquote(str(o)) for p, o in g.predicate_objects(s) if p != rdflib.RDF.type}
    text = s_clean + " " + " ".join(props.values())
    if "励磁系统" in text:
        types = [str(t).split('/')[-1] for t in g.objects(s, rdflib.RDF.type) if t != rdflib.OWL.NamedIndividual]
        if "Report" in "".join(types):
            continue
        print(f"[{types[0] if types else 'Thing'}] {s_clean.split('/')[-1]}")
        for k, v in props.items():
            if k != "label":
                print(f"    {k}: {v}")
