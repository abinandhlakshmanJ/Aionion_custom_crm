import frappe
def execute():
    scripts = frappe.db.get_all("CRM Form Script", filters={"dt": "CRM Lead", "view": "List", "enabled": 1}, fields=["name"])
    for s in scripts:
        print(s.name)
