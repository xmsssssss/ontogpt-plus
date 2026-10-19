import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

query = "励磁"
print(f"=== Searching for entities containing '{query}' ===")

for s, p, o in g:
    if p == rdflib.RDF.type and o == rdflib.OWL.NamedIndividual:
        s_str = unquote(str(s))
        label = g.value(s, rdflib.RDFS.label)
        label_str = unquote(str(label)) if label else ""
        
        # Check all literals under this subject
        literals = [unquote(str(val)) for _, val in g.predicate_objects(s) if isinstance(val, rdflib.Literal)]
        all_text = f"{s_str} {label_str} {' '.join(literals)}"
        
        if query in all_text:
            types = [str(t).split('/')[-1] for t in g.objects(s, rdflib.RDF.type) if t != rdflib.OWL.NamedIndividual]
            print(f"Match: {s_str.split('/')[-1]} | Class: {types} | Label: {label}")
            for prop, val in g.predicate_objects(s):
                if prop not in [rdflib.RDF.type, rdflib.RDFS.label]:
                    p_name = str(prop).split('/')[-1]
                    v_val = unquote(str(val)).split('/')[-1]
                    print(f"    -> {p_name}: {v_val}")
