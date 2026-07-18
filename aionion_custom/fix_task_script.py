import frappe

def execute():
    script = frappe.db.get_value("Server Script", "Scheduler Event For CRM Task", "script")
    if script:
        new_script = script.replace('window_end = frappe.utils.add_to_date(now, minutes=20)', 'window_end = frappe.utils.add_to_date(now, minutes=75)')
        frappe.db.set_value("Server Script", "Scheduler Event For CRM Task", "script", new_script)
        frappe.db.commit()
        print("Updated script successfully.")
    else:
        print("Script not found.")
