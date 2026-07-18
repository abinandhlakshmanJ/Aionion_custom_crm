import frappe

def execute():
    script = frappe.db.get_value("Server Script", "Scheduler Event For CRM Task", "script")
    
    # Change assignee logic to fallback to owner
    script = script.replace('assignee = task.get("assigned_to")\n    if not assignee:\n        continue', 
                            'assignee = task.get("assigned_to") or task.get("owner")\n    if not assignee:\n        continue')
    
    frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "script", script)
    frappe.db.commit()
    print("Updated assignee logic.")
