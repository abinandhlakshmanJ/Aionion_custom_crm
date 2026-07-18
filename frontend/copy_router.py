import os

source_path = '/home/abinandh/frappe/my-bench/apps/crm/frontend/src/router.js'
target_path = '/home/abinandh/frappe/my-bench/apps/aionion_custom/frontend/src/router.js'

with open(source_path, 'r') as f:
    text = f.read()

# Replace aliases so they pull from CRM instead of local
text = text.replace('@/', '@crm/')

# Fix the base URL
text = text.replace("createWebHistory('/crm')", "createWebHistory('/aionion_crm')")

# Fix the redirect in router.beforeEach
text = text.replace("redirect-to=/crm", "redirect-to=/aionion_crm")

with open(target_path, 'w') as f:
    f.write(text)
