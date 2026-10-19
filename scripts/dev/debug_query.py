import sys
from urllib.parse import unquote
import rdflib

# Force UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

query = "励磁系统"
print(f"=== Searching for query: '{query}' in extraction_result_optimized.owl ===")

matched_subjects = set()
for s, p, o in g:
    s_str = unquote(str(s))
    o_str = unquote(str(o))
    if query in s_str or query in o_str:
        matched_subjects.add(s)

print(f"Direct matched subjects with exact '{query}': {len(matched_subjects)}")
for s in list(matched_subjects)[:5]:
    label = g.value(s, rdflib.RDFS.label)
    print(f" - {s} | label: {label}")
