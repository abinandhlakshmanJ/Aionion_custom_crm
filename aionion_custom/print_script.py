import frappe

def execute():
    script = frappe.db.get_value("Server Script", "Scheduler Event For CRM Task", "script")
    print("---SCRIPT START---")
    print(script)
    print("---SCRIPT END---")
