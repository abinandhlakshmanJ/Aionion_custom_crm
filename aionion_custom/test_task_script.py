import frappe

def execute():
    script = frappe.db.get_value("Server Script", "Scheduler Event For CRM Task", "script")
    
    # Inject debug statements
    script = script.replace('count = 0', 'count = 0\nprint("Found tasks:", len(tasks))')
    script = script.replace('if not assignee:\n        continue', 'if not assignee:\n        print(task.name, "NO ASSIGNEE")\n        continue')
    script = script.replace('if already_sent:\n        continue', 'if already_sent:\n        print(task.name, "ALREADY SENT")\n        continue')
    script = script.replace('ignore_permissions=True)', 'ignore_permissions=True)\n    print(task.name, "INSERTED")')
    
    loc = locals()
    try:
        exec(script, globals(), loc)
    except Exception as e:
        print("Error executing:", str(e))
