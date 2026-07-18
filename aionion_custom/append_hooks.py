import os

hooks_path = "/home/abinandh/frappe/my-bench/apps/aionion_custom/aionion_custom/hooks.py"
with open(hooks_path, "a") as f:
    f.write('\noverride_whitelisted_methods = {\n    "crm.api.notifications.get_notifications": "aionion_custom.aionion_custom.overrides.notifications.get_notifications"\n}\n')
