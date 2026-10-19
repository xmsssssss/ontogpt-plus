import sys
from ontogpt.webapp.main import task_storage
sys.stdout.reconfigure(encoding='utf-8')

tasks = task_storage.list_tasks(limit=10)
for t in tasks:
    print(t['id'], t.get('title'), t.get('created_at'))
    detail = task_storage.get_task(t['id'])
    if detail and detail.get('result'):
        out = detail['result'].get('owl_output', '')
        print("   owl_output length:", len(out), "has BNode:", 'nodeID=' in out)
