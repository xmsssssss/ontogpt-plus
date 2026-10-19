import sys
from ontogpt.webapp.main import task_storage
from ontogpt.io.owl_builder import clean_and_upgrade_owl_xml
sys.stdout.reconfigure(encoding='utf-8')

print("Starting clean and upgrade for both tasks in database...")
for task_id in ['efd3b5c4-46bd-497c-b68a-576a06b02616', '8fe8b1ad-fb46-4115-9769-c188d20c8fb3']:
    detail = task_storage.get_task(task_id)
    if detail and detail.get('result'):
        raw_owl = detail['result'].get('owl_output', '')
        if raw_owl:
            print(f"Cleaning task {task_id} (len={len(raw_owl)})...")
            cleaned = clean_and_upgrade_owl_xml(raw_owl, schema_id="auto_schema_309c131b")
            res_dict = detail['result']
            res_dict['owl_output'] = cleaned
            task_storage.update_task_result(task_id, status='completed', result=res_dict)
            print(f"Task {task_id} upgraded successfully! (new_len={len(cleaned)})")
