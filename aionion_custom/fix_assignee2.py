import frappe
import re

def execute():
    script = frappe.db.get_value("Server Script", "Scheduler Event For CRM Task", "script")
    
    # Use regex to safely replace it regardless of \r or \n
    new_script = re.sub(
        r'assignee = task\.get\("assigned_to"\)\s+if not assignee:\s+continue',
        'assignee = task.get("assigned_to") or task.get("owner")\n    if not assignee:\n        continue',
        script
    )
    
    if new_script != script:
        frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "script", new_script)
        frappe.db.commit()
        print("Updated assignee logic successfully!")
    else:
        print("Failed to replace!")
