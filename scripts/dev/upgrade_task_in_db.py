import sys
from ontogpt.webapp.main import task_storage
from ontogpt.io.owl_builder import clean_and_upgrade_owl_xml
sys.stdout.reconfigure(encoding='utf-8')

detail = task_storage.get_task('efd3b5c4-46bd-497c-b68a-576a06b02616')
raw_owl = detail['result']['owl_output']
cleaned_owl = clean_and_upgrade_owl_xml(raw_owl, schema_id="auto_schema_309c131b")

# Update database
res_dict = detail['result']
res_dict['owl_output'] = cleaned_owl
task_storage.update_task_result('efd3b5c4-46bd-497c-b68a-576a06b02616', status='completed', result=res_dict)
print("Successfully upgraded task efd3b5c4 in SQLite database!")
