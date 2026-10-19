import sys, rdflib
from urllib.parse import unquote
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

g = rdflib.Graph()
g.parse(r'C:\Users\cj\Downloads\extraction_result_optimized.owl', format='xml')

entities_by_name = defaultdict(list)
smuggled_count = 0
noise_count = 0

for s in set(g.subjects(rdflib.RDF.type, rdflib.OWL.NamedIndividual)):
    s_clean = unquote(str(s)).split('/')[-1]
    
    # 检查实体名中是否有走私参数串（; 或 _key_ 之类）
    if ";" in s_clean or "_loop_type_" in s_clean or "_component_type_" in s_clean:
        smuggled_count += 1
        
    parts = s_clean.split("_")
    if len(parts) >= 3:
        c_name = parts[0]
        ent_name = "_".join(parts[1:-1])
        entities_by_name[(c_name, ent_name)].append(s_clean)

duplicates = {k: v for k, v in entities_by_name.items() if len(v) > 1}

print(f"Total unique (Class, Name) pairs: {len(entities_by_name)}")
print(f"Duplicated entity names across chunks: {len(duplicates)}")
print(f"Total entity IRIs with smuggled strings in name: {smuggled_count}")

print("\nTop duplicated entities across chunks:")
for (c, name), instances in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    print(f" - [{c}] {name} : appears {len(instances)} times")
