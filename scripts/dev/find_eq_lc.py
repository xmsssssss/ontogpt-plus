import sys, rdflib
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

print("Searching for any subjects matching 励磁系统:")
for s in set(g.subjects()):
    s_str = unquote(str(s))
    if "EquipmentComponent" in s_str and "励磁系统" in s_str:
        print("Found Subject:", s)
        for p, o in g.predicate_objects(s):
            print(f"   {str(p).split('/')[-1]} -> {unquote(str(o))}")
